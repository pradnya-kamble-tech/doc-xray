import dynamic from "next/dynamic"

const ViewerClient = dynamic(
    () => import("./ViewerClient").then((mod) => mod.ViewerClient),
    { ssr: false }
)

export default function ViewerPage({ params }: { params: { id: string } }) {
    // We use a separate Client component to manage state, SSE streaming, and interactivity
    return (
        <div className="flex-1 flex flex-col h-[calc(100vh-3.5rem)] overflow-hidden">
            <ViewerClient docId={params.id} />
        </div>
    )
}
