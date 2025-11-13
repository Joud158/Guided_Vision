from pyvis.network import Network
import networkx as nx
from typing import Dict, Optional, List
from pathlib import Path

class GraphVisualizer:
    def __init__(self, height: str = "500px", width: str = "800px"):
        """Initialize the graph visualizer.
        
        Args:
            height (str): Height of the visualization
            width (str): Width of the visualization
        """
        self.height = height
        self.width = width
        
        # Enhanced color scheme for hierarchical visualization
        self.node_colors = {
            # Scene level (Level 0) - High-level events
            'event': '#FF6B6B',      # Coral Red - for scene events
            'scene': '#FF6B6B',      # Coral Red
            'transition': '#FF8E53', # Orange Red
            
            # Action level (Level 1) - Mid-level actions  
            'action': '#4ECDC4',     # Teal - for actions
            'interaction': '#45B7D1', # Sky Blue
            'movement': '#96CEB4',   # Mint Green
            
            # Object level (Level 2) - Low-level objects
            'entity': '#FECA57',     # Golden Yellow - for entities
            'object': '#FF9FF3',     # Light Pink - for objects  
            'location': '#54A0FF',   # Bright Blue - for locations
            'state': '#5F27CD',      # Purple - for states
            
            # Special types
            'unknown': '#DDD',       # Light Gray - for unknown
            'temporal': '#C44569'    # Dark Pink - for temporal relationships
        }
        
        self.edge_colors = {
            # Scene level
            'leads_to': '#ff4500',  # Orange Red
            'transition': '#daa520',  # Goldenrod
            
            # Action level
            'performs': '#4169e1',  # Royal Blue
            'affects': '#8a2be2',  # Blue Violet
            
            # Object level
            'spatial': '#228b22',  # Forest Green
            'temporal': '#483d8b',  # Dark Slate Blue
            'state': '#cd853f',  # Peru
            'context': '#98fb98'  # Pale Green
        }
        
        # Confidence color scale
        self.confidence_colors = {
            'high': '#008000',  # Green
            'medium': '#ffa500',  # Orange
            'low': '#ff0000'  # Red
        }

    def create_hierarchical_visualization(
        self,
        scene_graph: nx.DiGraph,
        action_graph: nx.DiGraph,
        object_graph: nx.DiGraph,
        output_path: str
    ):
        """Create a hierarchical visualization of all graph layers.
        
        Args:
            scene_graph (nx.DiGraph): High-level scene events graph
            action_graph (nx.DiGraph): Mid-level actions graph
            object_graph (nx.DiGraph): Low-level objects graph
            output_path (str): Path to save the visualization
        """
        try:
            # Create network with physics enabled
            net = Network(
                height="450px",  # Further reduced to eliminate scrolling
                width="100%",
                directed=True,
                bgcolor="#ffffff",
                font_color="#333333"
            )
            
            # Configure physics for better centering and navigation
            net.set_options("""
            {
                "nodes": {
                    "font": {
                        "size": 12,
                        "face": "arial"
                    },
                    "size": 20,
                    "borderWidth": 2,
                    "borderWidthSelected": 4,
                    "shadow": true
                },
                "edges": {
                    "font": {
                        "size": 12,
                        "face": "arial"
                    },
                    "width": 2,
                    "shadow": true,
                    "smooth": {
                        "type": "cubicBezier",
                        "forceDirection": "vertical",
                        "roundness": 0.4
                    }
                },
                "physics": {
                    "enabled": true,
                    "stabilization": {
                        "enabled": true,
                        "iterations": 1000,
                        "updateInterval": 50,
                        "onlyDynamicEdges": false,
                        "fit": true
                    },
                    "hierarchicalRepulsion": {
                        "centralGravity": 0.5,
                        "springLength": 50,
                        "springConstant": 0.04,
                        "nodeDistance": 80,
                        "damping": 0.25
                    },
                    "solver": "hierarchicalRepulsion"
                },
                "layout": {
                    "hierarchical": {
                        "enabled": true,
                        "direction": "UD",
                        "sortMethod": "directed",
                        "levelSeparation": 60,
                        "nodeSpacing": 70,
                        "treeSpacing": 100
                    }
                },
                "interaction": {
                    "dragNodes": true,
                    "dragView": true,
                    "zoomView": true,
                    "selectConnectedEdges": true,
                    "hover": true,
                    "navigationButtons": true,
                    "keyboard": {
                        "enabled": true,
                        "speed": {
                            "x": 10,
                            "y": 10,
                            "zoom": 0.02
                        },
                        "bindToWindow": false
                    }
                }
            }
            """)
            
            # Check if any of the graphs have nodes
            if not any([scene_graph.number_of_nodes(), action_graph.number_of_nodes(), object_graph.number_of_nodes()]):
                # Add a placeholder node if all graphs are empty
                net.add_node(
                    "empty",
                    label="No data yet",
                    title="Waiting for input...",
                    color="#cccccc",
                    shape="text"
                )
            else:
                # Add scene graph nodes (top level)
                if scene_graph.number_of_nodes() > 0:
                    self._add_graph_layer(
                        net,
                        scene_graph,
                        "scene",
                        y_level=0
                    )
                
                # Add action graph nodes (middle level)
                if action_graph.number_of_nodes() > 0:
                    self._add_graph_layer(
                        net,
                        action_graph,
                        "action",
                        y_level=1
                    )
                
                # Add object graph nodes (bottom level)
                if object_graph.number_of_nodes() > 0:
                    self._add_graph_layer(
                        net,
                        object_graph,
                        "object",
                        y_level=2
                    )
                
                # Add cross-layer edges
                self._add_cross_layer_edges(
                    net,
                    scene_graph,
                    action_graph,
                    object_graph
                )
            
            # Add custom JavaScript for better navigation and centering
            net.html = net.html.replace(
                '</head>',
                '''
                <style>
                    #mynetwork {
                        width: 100% !important;
                        height: 450px !important;
                        background-color: #ffffff;
                        border: 1px solid #ddd;
                        border-radius: 4px;
                    }
                    .vis-network {
                        outline: none !important;
                    }
                    .node-tooltip {
                        position: absolute;
                        background-color: white;
                        padding: 10px;
                        border-radius: 4px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                        pointer-events: none;
                        z-index: 1000;
                        display: none;
                    }
                    .navigation-controls {
                        position: absolute;
                        top: 10px;
                        right: 10px;
                        z-index: 1000;
                        background: rgba(255, 255, 255, 0.9);
                        border-radius: 8px;
                        padding: 10px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                        display: flex;
                        flex-direction: column;
                        gap: 5px;
                    }
                    .nav-btn {
                        padding: 8px 12px;
                        background: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                        transition: background-color 0.3s;
                    }
                    .nav-btn:hover {
                        background: #45a049;
                    }
                    .nav-btn:active {
                        background: #3e8e41;
                    }
                    .status-info {
                        position: absolute;
                        bottom: 10px;
                        left: 10px;
                        background: rgba(0, 0, 0, 0.7);
                        color: white;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-size: 12px;
                        z-index: 1000;
                    }
                </style>
                </head>
                '''
            ).replace(
                '</body>',
                '''
                <div id="node-tooltip" class="node-tooltip"></div>
                <div class="navigation-controls">
                    <button class="nav-btn" onclick="fitNetwork()">📏 Fit All</button>
                    <button class="nav-btn" onclick="centerNetwork()">🎯 Center</button>
                    <button class="nav-btn" onclick="zoomIn()">🔍+ Zoom In</button>
                    <button class="nav-btn" onclick="zoomOut()">🔍- Zoom Out</button>
                    <button class="nav-btn" onclick="resetView()">🔄 Reset</button>
                </div>
                <div id="status-info" class="status-info">
                    Loading graph...
                </div>
                <script>
                    // Global network reference
                    let isStabilized = false;
                    const statusInfo = document.getElementById('status-info');
                    
                    // Update status
                    function updateStatus(message) {
                        statusInfo.textContent = message;
                    }
                    
                    // Navigation functions
                    function fitNetwork() {
                        network.fit({
                            animation: {
                                duration: 1000,
                                easingFunction: "easeInOutQuad"
                            }
                        });
                        updateStatus('Graph fitted to view');
                    }
                    
                    function centerNetwork() {
                        const nodes = network.body.data.nodes.get();
                        if (nodes.length > 0) {
                            network.focus(nodes[0].id, {
                                scale: 1.0,
                                animation: {
                                    duration: 1000,
                                    easingFunction: "easeInOutQuad"
                                }
                            });
                        }
                        updateStatus('Graph centered');
                    }
                    
                    function zoomIn() {
                        const scale = network.getScale();
                        network.moveTo({
                            scale: scale * 1.3,
                            animation: {
                                duration: 300,
                                easingFunction: "easeInOutQuad"
                            }
                        });
                        updateStatus(`Zoom: ${Math.round(scale * 1.3 * 100)}%`);
                    }
                    
                    function zoomOut() {
                        const scale = network.getScale();
                        network.moveTo({
                            scale: scale * 0.7,
                            animation: {
                                duration: 300,
                                easingFunction: "easeInOutQuad"
                            }
                        });
                        updateStatus(`Zoom: ${Math.round(scale * 0.7 * 100)}%`);
                    }
                    
                    function resetView() {
                        network.moveTo({
                            position: {x: 0, y: 0},
                            scale: 1.0,
                            animation: {
                                duration: 1000,
                                easingFunction: "easeInOutQuad"
                            }
                        });
                        updateStatus('View reset');
                    }
                    
                    // Enhanced tooltip functionality
                    const tooltip = document.getElementById('node-tooltip');
                    
                    network.on("hoverNode", function(params) {
                        const node = this.body.nodes[params.node];
                        if (node) {
                            const nodeData = node.options.data;
                            if (nodeData) {
                                tooltip.innerHTML = `
                                    <strong>${nodeData.label}</strong><br>
                                    Type: ${nodeData.type}<br>
                                    Level: ${nodeData.level}<br>
                                    ${nodeData.confidence ? `Confidence: ${nodeData.confidence.toFixed(2)}` : ''}
                                `;
                            } else {
                                tooltip.innerHTML = node.options.title || node.options.label;
                            }
                            tooltip.style.display = 'block';
                            tooltip.style.left = (params.event.center.x + 10) + 'px';
                            tooltip.style.top = (params.event.center.y - 10) + 'px';
                        }
                    });
                    
                    network.on("blurNode", function(params) {
                        tooltip.style.display = 'none';
                    });
                    
                    // Stabilization events
                    network.on("stabilizationProgress", function(params) {
                        const progress = Math.round(params.iterations / params.total * 100);
                        updateStatus(`Stabilizing: ${progress}%`);
                    });
                    
                    network.on("stabilizationIterationsDone", function() {
                        isStabilized = true;
                        updateStatus('Graph stabilized');
                        
                        // Auto-fit the graph after stabilization
                        setTimeout(() => {
                            fitNetwork();
                            updateStatus('Graph ready');
                        }, 500);
                    });
                    
                    // Enhanced click handling
                    network.on("click", function(params) {
                        if (params.nodes.length > 0) {
                            const nodeId = params.nodes[0];
                            network.focus(nodeId, {
                                scale: 1.2,
                                animation: {
                                    duration: 800,
                                    easingFunction: "easeInOutQuad"
                                }
                            });
                            updateStatus(`Focused on: ${nodeId}`);
                        } else {
                            // Clicked on empty space - center the view
                            const pointer = params.pointer.canvas;
                            network.moveTo({
                                position: network.canvasToDOM(pointer),
                                animation: {
                                    duration: 600,
                                    easingFunction: "easeInOutQuad"
                                }
                            });
                        }
                    });
                    
                    // Double click to fit
                    network.on("doubleClick", function(params) {
                        if (params.nodes.length === 0) {
                            fitNetwork();
                        }
                    });
                    
                    // Zoom event tracking
                    network.on("zoom", function(params) {
                        const scale = Math.round(params.scale * 100);
                        updateStatus(`Zoom: ${scale}%`);
                    });
                    
                    // Keyboard shortcuts
                    document.addEventListener('keydown', function(event) {
                        if (event.target.tagName.toLowerCase() !== 'input') {
                            switch(event.key) {
                                case 'f':
                                case 'F':
                                    fitNetwork();
                                    event.preventDefault();
                                    break;
                                case 'c':
                                case 'C':
                                    centerNetwork();
                                    event.preventDefault();
                                    break;
                                case '=':
                                case '+':
                                    zoomIn();
                                    event.preventDefault();
                                    break;
                                case '-':
                                case '_':
                                    zoomOut();
                                    event.preventDefault();
                                    break;
                                case 'r':
                                case 'R':
                                    resetView();
                                    event.preventDefault();
                                    break;
                            }
                        }
                    });
                    
                    // Initial setup
                    updateStatus('Graph loaded - use navigation controls or keyboard shortcuts (F: fit, C: center, +/-: zoom, R: reset)');
                </script>
                </body>
                '''
            )
            
            # Ensure the output directory exists
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the visualization
            net.save_graph(str(output_path))
            
        except Exception as e:
            print(f"Error creating visualization: {str(e)}")
            # Create a minimal error visualization
            net = Network(height="400px", width="100%")
            net.add_node(
                "error",
                label=f"Error: {str(e)}",
                color="#ff0000",
                shape="text"
            )
            net.save_graph(str(output_path))
            raise

    def _add_graph_layer(
        self,
        net: Network,
        graph: nx.DiGraph,
        layer_type: str,
        y_level: int
    ):
        """Add a layer of the hierarchical graph to the visualization.
        
        Args:
            net (Network): The pyvis network to add to
            graph (nx.DiGraph): The graph layer to add
            layer_type (str): Type of layer ('scene', 'action', or 'object')
            y_level (int): Vertical level in the hierarchy
        """
        # Add nodes
        for node, data in graph.nodes(data=True):
            # Get node type and confidence
            node_type = data.get('type', 'unknown')
            confidence = data.get('confidence', 0.8)
            
            # Create descriptive label based on layer type and available data
            label = self._create_descriptive_label(node, data, layer_type)
            
            # Add node with hierarchical positioning
            net.add_node(
                node,
                label=label,
                title=self._create_node_tooltip(data),
                color=self._get_node_color(layer_type, node_type),
                level=y_level,
                shape='dot' if node_type == 'location' else 'box',
                size=16 if confidence > 0.8 else 14,
                data={
                    'type': node_type,
                    'level': layer_type,
                    'confidence': confidence,
                    'label': label
                }
            )
        
        # Add edges within this layer
        for u, v, data in graph.edges(data=True):
            edge_type = data.get('type', 'unknown')
            confidence = data.get('confidence', 0.8)
            
            net.add_edge(
                u, v,
                title=f"Type: {edge_type}\nConfidence: {confidence:.2f}",
                color=self.edge_colors.get(edge_type, '#666666'),
                width=2 if confidence > 0.8 else 1,
                dashes=True if confidence < 0.6 else False
            )

    def _add_cross_layer_edges(
        self,
        net: Network,
        scene_graph: nx.DiGraph,
        action_graph: nx.DiGraph,
        object_graph: nx.DiGraph
    ):
        """Add edges between different layers of the hierarchy.
        
        Args:
            net (Network): The pyvis network to add to
            scene_graph (nx.DiGraph): High-level scene events graph
            action_graph (nx.DiGraph): Mid-level actions graph
            object_graph (nx.DiGraph): Low-level objects graph
        """
        # Connect scene events to their constituent actions
        for scene_node in scene_graph.nodes():
            scene_data = scene_graph.nodes[scene_node]
            
            # Find related actions
            for action_node in action_graph.nodes():
                action_data = action_graph.nodes[action_node]
                
                if self._are_nodes_related(scene_data, action_data):
                    net.add_edge(
                        scene_node,
                        action_node,
                        color="#666666",
                        dashes=True,
                        width=1,
                        title="Comprises"
                    )
        
        # Connect actions to involved objects
        for action_node in action_graph.nodes():
            action_data = action_graph.nodes[action_node]
            
            # Find related objects
            for object_node in object_graph.nodes():
                object_data = object_graph.nodes[object_node]
                
                if self._are_nodes_related(action_data, object_data):
                    net.add_edge(
                        action_node,
                        object_node,
                        color="#666666",
                        dashes=True,
                        width=1,
                        title="Involves"
                    )

    def _create_descriptive_label(self, node: str, data: Dict, layer_type: str) -> str:
        """Create descriptive labels for nodes based on their layer and data."""
        
        if layer_type == "scene":
            # Scene layer: Show event details
            if 'action' in data and 'subject' in data:
                action = data.get('action', '')
                subject = data.get('subject', '')
                obj = data.get('object', '')
                location = data.get('location', '')
                
                label = f"🎬 {action.title()}"
                if subject:
                    label += f"\n👤 {subject}"
                if obj:
                    label += f"\n🎯 {obj}"
                if location:
                    label += f"\n📍 {location}"
                return label
            else:
                return f"🎬 {str(node)}"
                
        elif layer_type == "action":
            # Action layer: Show verb, agent, and target
            verb = data.get('verb', '')
            agent = data.get('agent', '')
            target = data.get('target', '')
            manner = data.get('manner', '')
            
            if verb:
                label = f"⚡ {verb.title()}"
                if agent:
                    label += f"\n👤 {agent}"
                if target:
                    label += f"\n🎯 {target}"
                if manner:
                    label += f"\n🔧 {manner}"
                return label
            else:
                return f"⚡ {str(node)}"
                
        elif layer_type == "object":
            # Object layer: Show object type and attributes
            text = data.get('text', str(node))
            label_type = data.get('label', 'OBJECT')
            
            # Create more descriptive object labels
            if label_type == "PERSON":
                emoji = "👤"
            elif text.lower() in ['desk', 'table', 'chair']:
                emoji = "🪑"
            elif text.lower() in ['computer', 'laptop', 'screen']:
                emoji = "💻"
            elif text.lower() in ['coffee', 'mug', 'cup']:
                emoji = "☕"
            elif text.lower() in ['book', 'paper', 'document']:
                emoji = "📄"
            elif text.lower() in ['camera', 'phone']:
                emoji = "📱"
            elif text.lower() in ['shirt', 'clothing']:
                emoji = "👕"
            elif text.lower() in ['window', 'door']:
                emoji = "🏠"
            else:
                emoji = "📦"
            
            label = f"{emoji} {text.title()}"
            if label_type != "OBJECT":
                label += f"\n({label_type})"
            
            # Add any state information
            if 'state' in data and data['state']:
                label += f"\n🔄 {data['state']}"
                
            return label
        
        else:
            # Fallback for unknown layer types
            return str(node)

    def _get_node_color(self, layer_type: str, node_type: str) -> str:
        """Get the appropriate color for a node based on its layer and type."""
        # Assign colors primarily based on layer type for visual hierarchy
        if layer_type == "scene":
            # Scene layer - use red tones
            if node_type in ['event', 'scene']:
                return self.node_colors['scene']
            else:
                return self.node_colors['transition']
                
        elif layer_type == "action":
            # Action layer - use teal/blue tones
            if node_type == 'interaction':
                return self.node_colors['interaction']
            elif node_type == 'movement':
                return self.node_colors['movement']
            else:
                return self.node_colors['action']
                
        elif layer_type == "object":
            # Object layer - use yellow/pink tones
            if node_type == 'entity':
                return self.node_colors['entity']
            elif node_type == 'location':
                return self.node_colors['location']
            elif node_type == 'state':
                return self.node_colors['state']
            else:
                return self.node_colors['object']
        
        else:
            # Fallback for unknown layer types
            return self.node_colors.get(node_type, self.node_colors['unknown'])

    def _create_node_tooltip(self, data: Dict) -> str:
        """Create a detailed tooltip for a node."""
        tooltip = []
        
        # Add all non-empty attributes
        for key, value in data.items():
            # Skip empty values, embeddings (numpy arrays), and special keys
            if key not in ['id', 'label', 'embedding'] and value is not None:
                # Handle different value types
                if hasattr(value, '__len__') and not isinstance(value, str):
                    # Skip arrays/lists that aren't strings
                    continue
                elif value != '' and str(value).strip() != '':
                    tooltip.append(f"{key.title()}: {value}")
        
        return '<br>'.join(tooltip)

    def _are_nodes_related(self, data1: Dict, data2: Dict) -> bool:
        """Determine if two nodes from different layers are related."""
        # Extract all text values from both dictionaries, excluding arrays
        values1 = set()
        values2 = set()
        
        for v in data1.values():
            if v is not None and (not hasattr(v, '__len__') or isinstance(v, str)):
                values1.add(str(v).lower())
        
        for v in data2.values():
            if v is not None and (not hasattr(v, '__len__') or isinstance(v, str)):
                values2.add(str(v).lower())
        
        # Check for any overlap in values
        return bool(values1 & values2)

    def create_timeline_visualization(self, graphs: List[Dict], output_path: str):
        """Create a visualization showing graph evolution over time.
        
        Args:
            graphs (List[Dict]): List of graph states over time
            output_path (str): Path to save the visualization
        """
        # Create network for timeline view
        net = Network(
            height="800px",
            width="100%",
            directed=True,
            bgcolor="#ffffff",
            font_color="#333333"
        )
        
        # Configure physics for timeline layout
        net.set_options("""
        {
            "physics": {
                "enabled": true,
                "stabilization": {
                    "enabled": true,
                    "iterations": 100,
                    "updateInterval": 50
                },
                "barnesHut": {
                    "gravitationalConstant": -2000,
                    "centralGravity": 0.3,
                    "springLength": 200,
                    "springConstant": 0.04,
                    "damping": 0.09
                }
            },
            "layout": {
                "hierarchical": {
                    "enabled": true,
                    "direction": "LR",
                    "sortMethod": "directed",
                    "levelSeparation": 250,
                    "nodeSpacing": 200
                }
            }
        }
        """)
        
        # Add timeline nodes
        for i, graph_state in enumerate(graphs):
            timestamp = graph_state.get('timestamp', f'T{i}')
            
            # Add nodes for this timestamp
            for node in graph_state['nodes']:
                node_id = f"{timestamp}_{node['id']}"
                node_type = node['data'].get('type', 'unknown')
                
                net.add_node(
                    node_id,
                    label=f"{node['id']}\n{timestamp}",
                    title=self._create_node_tooltip(node['data']),
                    color=self.node_colors.get(node_type, '#cccccc'),
                    level=i  # Use timestamp as level for horizontal layout
                )
            
            # Add edges for this timestamp
            for edge in graph_state['edges']:
                from_id = f"{timestamp}_{edge['source']}"
                to_id = f"{timestamp}_{edge['target']}"
                edge_type = edge['data'].get('type', 'unknown')
                
                net.add_edge(
                    from_id,
                    to_id,
                    title=self._create_node_tooltip(edge['data']),
                    color=self.edge_colors.get(edge_type, '#666666')
                )
            
            # Add temporal edges to previous timestamp
            if i > 0:
                prev_timestamp = graphs[i-1].get('timestamp', f'T{i-1}')
                for node in graph_state['nodes']:
                    curr_id = f"{timestamp}_{node['id']}"
                    prev_id = f"{prev_timestamp}_{node['id']}"
                    
                    if prev_id in net.get_nodes():
                        net.add_edge(
                            prev_id,
                            curr_id,
                            color=self.edge_colors['temporal'],
                            dashes=True,
                            width=1
                        )
        
        # Save the visualization
        net.save_graph(output_path) 