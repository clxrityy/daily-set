package main

import (
	"encoding/json"
	"net/http"
	"testing"
	"time"

	jwt "github.com/golang-jwt/jwt/v5"
	nats "github.com/nats-io/nats.go"
)

func TestValidateJWTAnonAllowed(t *testing.T) {
	user, err := validateJWT("", "")
	if err != nil {
		t.Fatalf("expected anon allowed without secret, got err: %v", err)
	}
	if user != "anon" {
		t.Fatalf("expected anon user, got %q", user)
	}
}

func TestValidateJWTValidAndInvalid(t *testing.T) {
	secret := "s3cr3t"
	// valid token with sub
	tok := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"sub": "u123",
		"iat": time.Now().Unix(),
	})
	s, err := tok.SignedString([]byte(secret))
	if err != nil {
		t.Fatalf("sign failed: %v", err)
	}
	uid, err := validateJWT(s, secret)
	if err != nil || uid != "u123" {
		t.Fatalf("expected uid u123, got %q err=%v", uid, err)
	}
	// invalid token
	if _, err := validateJWT("not-a-token", secret); err == nil {
		t.Fatalf("expected error for invalid token")
	}
}

func TestExtractTokenHeaderAndQuery(t *testing.T) {
	r, _ := http.NewRequest("GET", "http://example/ws?token=qparam", nil)
	r.Header.Set("Authorization", "Bearer headerToken")
	if got := extractToken(r); got != "headerToken" {
		t.Fatalf("header should win, got %q", got)
	}
	r2, _ := http.NewRequest("GET", "http://example/ws?token=onlyQuery", nil)
	if got := extractToken(r2); got != "onlyQuery" {
		t.Fatalf("expected query token, got %q", got)
	}
}

func TestJoinLeaveRoom(t *testing.T) {
	srv := NewRealtimeServer((*nats.Conn)(nil))
	c := &Client{id: "c1", rooms: map[string]struct{}{}, conn: nil}
	srv.joinRoom(c, "room1")
	srv.roomsMu.RLock()
	if _, ok := srv.rooms["room1"][c]; !ok {
		t.Fatalf("client not in room after join")
	}
	srv.roomsMu.RUnlock()
	srv.leaveAll(c)
	srv.roomsMu.RLock()
	if _, ok := c.rooms["room1"]; ok {
		t.Fatalf("client should be removed from its own room list")
	}
	if _, ok := srv.rooms["room1"]; ok {
		t.Fatalf("room should be deleted when empty")
	}
	srv.roomsMu.RUnlock()
}

func TestPublishActionNoNATSNoPanic(t *testing.T) {
	srv := NewRealtimeServer((*nats.Conn)(nil))
	env := &Envelope{V: 1, Type: "action", Room: "r"}
	// Should not panic when NATS is nil
	srv.publishAction(env)
}

func TestExponentialBackoffCaps(t *testing.T) {
	for i := 0; i < 10; i++ {
		d := exponentialBackoff(i)
		if d <= 0 {
			t.Fatalf("backoff non-positive: %v", d)
		}
		if d > 11*time.Second { // cap (10s) + jitter safety margin
			t.Fatalf("backoff too large: %v", d)
		}
	}
}

func TestHandleRoomUpdateNoPeersNoPanic(t *testing.T) {
	srv := NewRealtimeServer((*nats.Conn)(nil))
	// No clients joined; should be a no-op
	env := Envelope{V: 1, Type: "update"}
	b, _ := json.Marshal(env)
	m := &nats.Msg{Subject: "room.testroom.update", Data: b}
	srv.handleRoomUpdate(m)
}
