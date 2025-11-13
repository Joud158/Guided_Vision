from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from pathlib import Path
import traceback
import json

from scene_graph.hierarchical_graph_builder import HierarchicalGraphBuilder
from scene_graph.graph_store import GraphStore
from scene_graph.graph_visualizer import GraphVisualizer

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"]
)

# Create output directory if it doesn't exist
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

# Mount the output directory for static file serving with CORS headers
app.mount("/output", StaticFiles(directory="output", html=True), name="output")

# Initialize components
graph_builder = HierarchicalGraphBuilder(context_window_size=5)
graph_store = GraphStore()
graph_visualizer = GraphVisualizer()

def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse timestamp string to datetime object.
    
    Args:
        timestamp_str: ISO format timestamp string
        
    Returns:
        datetime object
    """
    try:
        return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    except ValueError as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}")
        return datetime.now()

class CaptionRequest(BaseModel):
    caption: str
    timestamp: Optional[str] = None

@app.post("/process_caption")
async def process_caption(request: CaptionRequest):
    """Process a caption and update the scene graph."""
    try:
        print(f"[DEBUG] Received request from client")
        print(f"[DEBUG] Processing caption: {request.caption}")
        
        # Parse timestamp if provided, otherwise use current time
        timestamp = datetime.now()
        if request.timestamp:
            timestamp = parse_timestamp(request.timestamp)
        
        # Update scene graphs
        scene_graph, action_graph, object_graph = graph_builder.update_scene_state(
            request.caption,
            timestamp.timestamp()
        )
        print("[DEBUG] Scene graphs updated")
        
        # Get graph data for response
        graph_data = graph_builder.get_graph_data()
        
        # Create visualization
        viz_filename = f"scene_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.html"
        viz_path = output_dir / viz_filename
        
        # Create hierarchical visualization
        graph_visualizer.create_hierarchical_visualization(
            scene_graph,
            action_graph,
            object_graph,
            str(viz_path)
        )
        
        response_data = {
            "status": "success",
            "message": "Scene updated",
            "graph_data": graph_data,
            "visualization_path": f"/output/{viz_filename}"
        }
        print(f"[DEBUG] Sending response: {response_data['status']}")
        
        return response_data
        
    except Exception as e:
        print(f"[ERROR] Error processing caption: {str(e)}")
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.post("/reset_graph")
async def reset_graph():
    """Reset the scene graph to start fresh."""
    try:
        graph_builder.reset_graphs()
        return {"status": "success", "message": "Scene graphs reset successfully"}
    except Exception as e:
        print(f"Error resetting graph: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.get("/visualize/{session_id}")
async def visualize_session(session_id: str):
    """Get visualization for a specific session."""
    try:
        # Load session data
        graphs = graph_store.load_session(session_id)
        print(f"Loaded session {session_id} with {len(graphs)} graphs")
        
        # Create timeline visualization
        output_path = output_dir / f"session_{session_id}_timeline.html"
        graph_visualizer.create_timeline_visualization(graphs, str(output_path))
        print(f"Created timeline visualization at: {output_path}")
        
        return FileResponse(output_path)
        
    except Exception as e:
        print(f"Error visualizing session: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.get("/sessions")
async def list_sessions():
    """List all available sessions."""
    try:
        sessions = []
        for file in graph_store.storage_dir.glob("session_*.json"):
            session_id = file.stem.replace("session_", "")
            sessions.append(session_id)
        print(f"Found {len(sessions)} sessions")
        return {"sessions": sessions}
    except Exception as e:
        print(f"Error listing sessions: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.get("/export_graph")
async def export_graph():
    """Export the current graph in JSON format."""
    try:
        # Get all graph layers
        graph_data = graph_builder.get_graph_data()
        
        content = json.dumps(graph_data, indent=2)
        content_type = 'application/json'
        filename = 'scene_graphs.json'
            
        # Create response with appropriate headers
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        return Response(
            content=content,
            media_type=content_type,
            headers=headers
        )
        
    except Exception as e:
        print(f"Error exporting graph: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "traceback": traceback.format_exc()
            }
        )

@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "healthy", "message": "Scene graph server is running"}

# Add CORS headers to all responses
@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081) 