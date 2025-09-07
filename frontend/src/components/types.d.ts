declare module './Card' {
    export const CardView: (props: {
        readonly card: [number, number, number, number]
        readonly idx: number
        readonly selected?: boolean
        readonly onSelect?: (idx: number) => void
    }) => JSX.Element
}
