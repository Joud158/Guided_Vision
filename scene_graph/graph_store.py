import json
from datetime import datetime
from typing import Dict, List, Optional
import networkx as nx
from pathlib import Path

class GraphStore:
    def __init__(self, storage_dir: str = "output"):
        """Initialize the graph store.
        
        Args:
            storage_dir (str): Directory to store graph data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.session_graphs: List[Dict] = []
        
    def add_graph(self, graph: nx.DiGraph, timestamp: Optional[datetime] = None):
        """Add a graph to the current session with timestamp.
        
        Args:
            graph (nx.DiGraph): The scene graph to store
            timestamp (datetime, optional): Timestamp for the graph. Defaults to current time.
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        graph_data = {
            'timestamp': timestamp.isoformat(),
            'nodes': [{'id': node, 'type': data.get('type', 'unknown')} 
                     for node, data in graph.nodes(data=True)],
            'edges': [{'from': u, 'to': v, 'relationship': data.get('relationship', '')} 
                     for u, v, data in graph.edges(data=True)]
        }
        
        self.session_graphs.append(graph_data)
        
    def save_session(self, session_id: Optional[str] = None):
        """Save the current session to a JSON file.
        
        Args:
            session_id (str, optional): Custom session ID. Defaults to timestamp.
        """
        if not session_id:
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            
        output_file = self.storage_dir / f"session_{session_id}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                'session_id': session_id,
                'graphs': self.session_graphs
            }, f, indent=2)
            
    def load_session(self, session_id: str) -> List[Dict]:
        """Load a previous session from file.
        
        Args:
            session_id (str): ID of the session to load
            
        Returns:
            List[Dict]: List of graph data from the session
        """
        input_file = self.storage_dir / f"session_{session_id}.json"
        
        if not input_file.exists():
            raise FileNotFoundError(f"Session file not found: {input_file}")
            
        with open(input_file, 'r') as f:
            data = json.load(f)
            self.session_graphs = data['graphs']
            return self.session_graphs
            
    def query_timespan(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Query graphs within a specific timespan.
        
        Args:
            start_time (datetime): Start of the timespan
            end_time (datetime): End of the timespan
            
        Returns:
            List[Dict]: List of graphs within the timespan
        """
        return [
            graph for graph in self.session_graphs
            if start_time <= datetime.fromisoformat(graph['timestamp']) <= end_time
        ] 