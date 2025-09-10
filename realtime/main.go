package main

import (
	"context"
	"crypto/rand"
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"math"
	"math/big"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	jwt "github.com/golang-jwt/jwt/v5"
	nats "github.com/nats-io/nats.go"
	ws "nhooyr.io/websocket"
	"nhooyr.io/websocket/wsjson"
)

// Envelope is the cross-service message format.
type Envelope struct {
	V       int             `json:"v"`
	Type    string          `json:"type"`
	Room    string          `json:"room,omitempty"`
	From    string          `json:"from,omitempty"`
	ID      string          `json:"id"`
	TS      time.Time       `json:"ts"`
	Payload json.RawMessage `json:"payload"`
}

// Client represents a connected websocket client.
type Client struct {
	id     string
	userID string
	conn   *ws.Conn
	mu     sync.Mutex // protects writes to conn
	rooms  map[string]struct{}
}

func (c *Client) send(ctx context.Context, v any) error {
	c.mu.Lock()
	defer c.mu.Unlock()
	return wsjson.Write(ctx, c.conn, v)
}

// RealtimeServer holds state for WS <-> NATS bridging.
type RealtimeServer struct {
	nats *nats.Conn
	// room -> set of clients
	roomsMu sync.RWMutex
	rooms   map[string]map[*Client]struct{}
}

func NewRealtimeServer(nc *nats.Conn) *RealtimeServer {
	return &RealtimeServer{
		nats:  nc,
		rooms: make(map[string]map[*Client]struct{}),
	}
}

func (s *RealtimeServer) joinRoom(c *Client, room string) {
	s.roomsMu.Lock()
	defer s.roomsMu.Unlock()
	if s.rooms[room] == nil {
		s.rooms[room] = make(map[*Client]struct{})
	}
	s.rooms[room][c] = struct{}{}
	c.rooms[room] = struct{}{}
}

func (s *RealtimeServer) leaveAll(c *Client) {
	s.roomsMu.Lock()
	defer s.roomsMu.Unlock()
	for room := range c.rooms {
		if peers, ok := s.rooms[room]; ok {
			delete(peers, c)
			if len(peers) == 0 {
				delete(s.rooms, room)
			}
		}
		// Also clear the client's own membership record
		delete(c.rooms, room)
	}
}

func randomID() string {
	const alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
	n := 16
	b := make([]byte, n)
	for i := 0; i < n; i++ {
		x, _ := rand.Int(rand.Reader, big.NewInt(int64(len(alphabet))))
		b[i] = alphabet[x.Int64()]
	}
	return string(b)
}

func validateJWT(tokenStr, secret string) (string, error) {
	if secret == "" {
		// Allow anonymous when no secret configured (dev)
		return "anon", nil
	}
	token, err := jwt.Parse(tokenStr, func(t *jwt.Token) (interface{}, error) {
		if _, ok := t.Method.(*jwt.SigningMethodHMAC); !ok {
			return nil, fmt.Errorf("unexpected signing method: %v", t.Header["alg"])
		}
		return []byte(secret), nil
	})
	if err != nil || !token.Valid {
		return "", errors.New("invalid token")
	}
	// Extract sub or uid claim
	if claims, ok := token.Claims.(jwt.MapClaims); ok {
		if sub, ok := claims["sub"].(string); ok && sub != "" {
			return sub, nil
		}
		if uid, ok := claims["uid"].(string); ok && uid != "" {
			return uid, nil
		}
	}
	return "", errors.New("missing subject")
}

// extractToken extracts the JWT token from the request
func extractToken(r *http.Request) string {
	token := ""
	if auth := r.Header.Get("Authorization"); strings.HasPrefix(strings.ToLower(auth), "bearer ") {
		token = strings.TrimSpace(auth[7:])
	}
	if token == "" {
		token = r.URL.Query().Get("token")
	}
	return token
}

// handleClientMessages processes incoming messages from a client
func (s *RealtimeServer) handleClientMessages(ctx context.Context, client *Client) {
	for {
		var env Envelope
		if err := wsjson.Read(ctx, client.conn, &env); err != nil {
			log.Printf("read error: %v", err)
			break
		}

		// Set defaults for missing values
		if env.V == 0 {
			env.V = 1
		}
		if env.ID == "" {
			env.ID = randomID()
		}
		if env.TS.IsZero() {
			env.TS = time.Now().UTC()
		}

		if !s.processMessage(ctx, client, &env) {
			break
		}
	}

	// connection closed - cleanup
	s.leaveAll(client)
	_ = client.conn.Close(ws.StatusNormalClosure, "bye")
}

// processMessage handles different message types
func (s *RealtimeServer) processMessage(ctx context.Context, client *Client, env *Envelope) bool {
	switch env.Type {
	case "ping":
		_ = client.send(ctx, Envelope{V: 1, Type: "pong", ID: env.ID, TS: time.Now().UTC()})
	case "subscribe":
		if env.Room != "" {
			s.joinRoom(client, env.Room)
			// Optionally ack
			_ = client.send(ctx, Envelope{V: 1, Type: "subscribed", Room: env.Room, ID: env.ID, TS: time.Now().UTC()})
		}
	case "action":
		s.publishAction(env)
	default:
		// ignore or echo
	}
	return true
}

// publishAction publishes an action to NATS
func (s *RealtimeServer) publishAction(env *Envelope) {
	if s.nats == nil {
		return
	}

	subj := fmt.Sprintf("room.%s.action", env.Room)
	b, _ := json.Marshal(env)
	if err := s.nats.Publish(subj, b); err != nil {
		log.Printf("nats publish error: %v", err)
	}
}

// setupRoomSubscription sets up NATS subscription for room updates
func (s *RealtimeServer) setupRoomSubscription() (*nats.Subscription, error) {
	if s.nats == nil {
		return nil, nil
	}

	return s.nats.Subscribe("room.*.update", func(m *nats.Msg) {
		s.handleRoomUpdate(m)
	})
}

// handleRoomUpdate processes room update messages from NATS
func (s *RealtimeServer) handleRoomUpdate(m *nats.Msg) {
	// Parse room ID from subject
	parts := strings.Split(m.Subject, ".")
	if len(parts) < 3 {
		return
	}
	roomID := parts[1]

	var env Envelope
	if err := json.Unmarshal(m.Data, &env); err != nil {
		return
	}
	env.V = 1
	env.TS = time.Now().UTC()

	// Deliver to clients in room
	s.roomsMu.RLock()
	peers := s.rooms[roomID]
	for peer := range peers {
		// Write with short timeout
		pctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		_ = peer.send(pctx, env)
		cancel()
	}
	s.roomsMu.RUnlock()
}

// startKeepAlive starts the keep-alive ping mechanism
func startKeepAlive(ctx context.Context, client *Client) {
	ticker := time.NewTicker(25 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			// Best-effort ping
			_ = client.send(context.Background(), Envelope{V: 1, Type: "ping", ID: randomID(), TS: time.Now().UTC()})
		}
	}
}

func (s *RealtimeServer) wsHandler(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	conn, err := ws.Accept(w, r, &ws.AcceptOptions{
		InsecureSkipVerify: true,
		OriginPatterns:     []string{"*"},
	})
	if err != nil {
		log.Printf("ws accept error: %v", err)
		return
	}
	defer conn.Close(ws.StatusNormalClosure, "bye")

	// Authenticate client
	token := extractToken(r)
	secret := os.Getenv("REALTIME_JWT_SECRET")
	userID, err := validateJWT(token, secret)
	if err != nil {
		log.Printf("auth failed: %v", err)
		conn.Close(ws.StatusPolicyViolation, "unauthorized")
		return
	}

	// Create client
	client := &Client{id: randomID(), userID: userID, conn: conn, rooms: map[string]struct{}{}}
	log.Printf("client connected uid=%s cid=%s", userID, client.id)

	// Start message handling loop
	go s.handleClientMessages(ctx, client)

	// Set up room subscription
	sub, err := s.setupRoomSubscription()
	if err != nil {
		log.Printf("nats subscribe error: %v", err)
	}
	if sub != nil {
		defer sub.Unsubscribe()
	}

	// Start keep-alive mechanism
	startKeepAlive(ctx, client)
}

func exponentialBackoff(attempt int) time.Duration {
	// 250ms * 2^attempt with jitter, capped at 10s
	base := 250 * time.Millisecond
	d := time.Duration(float64(base) * math.Pow(2, float64(attempt)))
	if d > 10*time.Second {
		d = 10 * time.Second
	}
	// add 0-250ms jitter
	j := time.Duration(randInt(0, 250)) * time.Millisecond
	return d + j
}

func randInt(min, max int) int {
	if max <= min {
		return min
	}
	n, _ := rand.Int(rand.Reader, big.NewInt(int64(max-min)))
	return int(n.Int64()) + min
}

func main() {
	// NATS connection optional
	natsURL := os.Getenv("NATS_URL")
	var nc *nats.Conn
	var err error
	if natsURL != "" {
		nc, err = nats.Connect(natsURL, nats.Name("daily-set-realtime"))
		if err != nil {
			log.Printf("failed to connect NATS: %v", err)
		} else {
			log.Printf("connected to NATS at %s", natsURL)
		}
	}

	srv := NewRealtimeServer(nc)
	http.HandleFunc("/ws", srv.wsHandler)
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte(`{"status":"ok"}`))
	})

	addr := os.Getenv("REALTIME_ADDR")
	if addr == "" {
		addr = ":8081"
	}
	log.Printf("realtime server listening on %s", addr)
	if err := http.ListenAndServe(addr, nil); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
