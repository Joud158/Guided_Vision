import spacy
import networkx as nx
from typing import List, Dict, Set
from datetime import datetime
import json

class SceneGraphBuilder:
    def __init__(self):
        """Initialize the SceneGraphBuilder with spaCy for NLP processing."""
        self.nlp = spacy.load("en_core_web_sm")
        self.scene_graph = nx.DiGraph()  # Current state of the scene
        
        # Track main scene components
        self.main_entities = set()  # Track main entities (people, objects)
        self.locations = {}  # Track where things are
        self.states = {}  # Track states of entities
        self.actions = {}  # Track current actions
        
        # Define important elements to track
        self.important_objects = {
            'person', 'people', 'man', 'woman', 'student', 'teacher',
            'desk', 'table', 'chair', 'computer', 'laptop', 'screen',
            'phone', 'book', 'paper', 'document', 'window', 'door',
            'keyboard', 'mouse', 'camera'
        }
        
        self.important_actions = {
            'sit', 'stand', 'walk', 'move', 'type', 'write', 'read',
            'look', 'watch', 'hold', 'pick', 'put', 'open', 'close'
        }
        
        self.important_states = {
            'sitting', 'standing', 'walking', 'working', 'reading',
            'writing', 'typing', 'looking', 'holding'
        }
        
    def is_important_element(self, text: str, element_type: str) -> bool:
        """Determine if an element is important enough to track."""
        text = text.lower()
        
        if element_type == 'entity':
            # Check if it contains any important object terms
            return any(obj in text for obj in self.important_objects)
        elif element_type == 'action':
            # Check if it's an important action
            return any(action in text for action in self.important_actions)
        elif element_type == 'state':
            # Check if it's an important state
            return any(state in text for state in self.important_states)
        
        return False
    
    def extract_scene_elements(self, caption: str) -> Dict:
        """Extract key elements from the scene description."""
        doc = self.nlp(caption)
        
        elements = {
            'entities': set(),  # People and main objects
            'locations': {},    # Spatial relationships
            'states': {},       # States and attributes
            'actions': {},      # Current actions
            'relationships': [] # Other relationships
        }
        
        # First pass: collect all important entities
        important_entities = set()
        for chunk in doc.noun_chunks:
            if (chunk.root.pos_ not in ['PRON', 'DET'] and 
                self.is_important_element(chunk.text, 'entity')):
                # Get full noun phrase with modifiers
                modifiers = ' '.join([token.text for token in chunk if token.dep_ in ['amod', 'compound']])
                entity = chunk.root.text if not modifiers else f"{modifiers} {chunk.root.text}"
                entity = entity.lower()
                important_entities.add(entity)
                elements['entities'].add(entity)
        
        # Second pass: extract relationships
        for token in doc:
            # Extract verb-based relationships
            if token.pos_ == "VERB":
                # Find subject
                subj = None
                for child in token.children:
                    if child.dep_ in ["nsubj", "nsubjpass"]:
                        # Get the full subject phrase
                        subj_text = ' '.join([w.text for w in child.subtree]).lower()
                        # Check if it contains any important entity
                        if any(entity in subj_text for entity in important_entities):
                            subj = subj_text
                            break
                
                # Find object
                obj = None
                for child in token.children:
                    if child.dep_ in ["dobj", "pobj", "attr"]:
                        # Get the full object phrase
                        obj_text = ' '.join([w.text for w in child.subtree]).lower()
                        # Check if it contains any important entity
                        if any(entity in obj_text for entity in important_entities):
                            obj = obj_text
                            break
                
                # Find location
                loc = None
                for child in token.children:
                    if child.dep_ == "prep" and child.text.lower() in ["in", "on", "at", "near", "by", "behind", "in front of"]:
                        for grandchild in child.children:
                            if grandchild.dep_ == "pobj":
                                loc_text = ' '.join([w.text for w in grandchild.subtree]).lower()
                                if any(entity in loc_text for entity in important_entities):
                                    loc = (child.text.lower(), loc_text)
                                    break
                
                # Add relationships
                if subj:
                    if self.is_important_element(token.text, 'action'):
                        elements['actions'][subj] = token.text.lower()
                    if obj:
                        elements['relationships'].append((subj, token.text.lower(), obj))
                    if loc:
                        elements['locations'][subj] = loc
            
            # Extract spatial relationships
            elif token.dep_ == "prep" and token.head.pos_ in ["NOUN", "PROPN"]:
                head_text = ' '.join([w.text for w in token.head.subtree]).lower()
                if any(entity in head_text for entity in important_entities):
                    for child in token.children:
                        if child.dep_ == "pobj":
                            obj_text = ' '.join([w.text for w in child.subtree]).lower()
                            if any(entity in obj_text for entity in important_entities):
                                elements['locations'][head_text] = (token.text.lower(), obj_text)
            
            # Extract states
            elif token.pos_ == "ADJ" and token.dep_ == "amod":
                head_text = ' '.join([w.text for w in token.head.subtree]).lower()
                if any(entity in head_text for entity in important_entities):
                    if self.is_important_element(token.text, 'state'):
                        elements['states'][head_text] = token.text.lower()
        
        return elements
    
    def _infer_relationships(self):
        """Infer relationships between disconnected nodes based on context."""
        # Get all nodes without any edges
        isolated_nodes = list(nx.isolates(self.scene_graph))
        
        # Get all nodes by type
        entity_nodes = [n for n, d in self.scene_graph.nodes(data=True) if d.get('type') == 'entity']
        location_nodes = [n for n, d in self.scene_graph.nodes(data=True) if d.get('type') == 'location']
        
        # First, connect entities to their corresponding locations
        for entity in entity_nodes:
            # Look for locations that mention this entity
            for loc in location_nodes:
                if entity.lower() in loc.lower():
                    # If entity "desk" is mentioned in location "front of a desk"
                    self.scene_graph.add_edge(
                        entity,
                        loc,
                        type='spatial',
                        relationship='at'
                    )
        
        # Then connect entities that share locations
        location_to_entities = {}
        for loc in location_nodes:
            # Get all entities connected to this location
            connected_entities = set()
            for edge in self.scene_graph.edges(data=True):
                if edge[1] == loc and self.scene_graph.nodes[edge[0]].get('type') == 'entity':
                    connected_entities.add(edge[0])
            location_to_entities[loc] = connected_entities
        
        # Connect entities that share locations
        for loc, entities in location_to_entities.items():
            entities = list(entities)
            for i in range(len(entities)):
                for j in range(i + 1, len(entities)):
                    if not self.scene_graph.has_edge(entities[i], entities[j]):
                        self.scene_graph.add_edge(
                            entities[i],
                            entities[j],
                            type='context',
                            relationship='near'
                        )
        
        # Finally, connect any remaining isolated entities
        isolated_nodes = list(nx.isolates(self.scene_graph))
        connected_entities = [n for n in entity_nodes if n not in isolated_nodes]
        
        for isolated_node in isolated_nodes:
            # Skip if not an entity
            if self.scene_graph.nodes[isolated_node].get('type') != 'entity':
                continue
                
            # Try to find the most relevant connected entity to link with
            for connected_node in connected_entities:
                self.scene_graph.add_edge(
                    isolated_node,
                    connected_node,
                    type='context',
                    relationship='seen_with'
                )
                break  # Only create one connection per isolated node
    
    def update_scene_state(self, caption: str) -> nx.DiGraph:
        """Update the scene graph based on new caption."""
        print(f"Processing caption: {caption}")
        
        # Extract new scene elements
        elements = self.extract_scene_elements(caption)
        print(f"Extracted elements: {elements}")
        
        # Update main entities
        self.main_entities.update(elements['entities'])
        
        # Update or add nodes for important entities
        for entity in self.main_entities:
            if entity not in self.scene_graph:
                self.scene_graph.add_node(entity, type='entity')
            
            # Update node attributes
            if entity in elements['states']:
                self.scene_graph.nodes[entity]['state'] = elements['states'][entity]
            if entity in elements['actions']:
                self.scene_graph.nodes[entity]['action'] = elements['actions'][entity]
        
        # Update locations
        for entity, (prep, location) in elements['locations'].items():
            # Add location node if new
            if location not in self.scene_graph:
                self.scene_graph.add_node(location, type='location')
            
            # Update spatial relationship
            if entity in self.scene_graph and location in self.scene_graph:
                self.scene_graph.add_edge(entity, location, type='spatial', relationship=prep)
                self.locations[entity] = (prep, location)
        
        # Update relationships
        for subj, pred, obj in elements['relationships']:
            # Add any missing nodes
            for node in [subj, obj]:
                if node not in self.scene_graph:
                    self.scene_graph.add_node(node, type='entity')
            
            # Add the relationship edge
            self.scene_graph.add_edge(subj, obj, type='action', relationship=pred)
        
        # Infer relationships for isolated nodes
        self._infer_relationships()
        
        # Clean up the graph
        self._clean_stale_edges()
        
        print(f"Scene graph updated - {len(self.scene_graph.nodes)} nodes, {len(self.scene_graph.edges)} edges")
        return self.scene_graph
    
    def _clean_stale_edges(self):
        """Remove edges that no longer represent current state."""
        edges_to_remove = []
        for u, v, data in self.scene_graph.edges(data=True):
            # Keep if it's a current location
            if data['type'] == 'spatial' and u in self.locations:
                prep, loc = self.locations[u]
                if v != loc or data['relationship'] != prep:
                    edges_to_remove.append((u, v))
            # Keep if it's a current action
            elif data['type'] == 'action' and u in self.actions:
                if data['relationship'] != self.actions[u]:
                    edges_to_remove.append((u, v))
        
        self.scene_graph.remove_edges_from(edges_to_remove)
        
        # Remove duplicate location nodes
        location_groups = {}
        for node, data in self.scene_graph.nodes(data=True):
            if data.get('type') == 'location':
                # Create a normalized key for the location
                key = ''.join(c.lower() for c in node if c.isalnum())
                if key not in location_groups:
                    location_groups[key] = []
                location_groups[key].append(node)
        
        # For each group of similar locations, keep the one with most connections
        for locations in location_groups.values():
            if len(locations) > 1:
                # Sort by number of connections
                locations.sort(key=lambda x: len(list(self.scene_graph.edges(x))) + len(list(self.scene_graph.in_edges(x))), reverse=True)
                # Keep the first one, remove others
                for loc in locations[1:]:
                    # Transfer all edges to the kept location
                    for u, v, data in list(self.scene_graph.edges(loc, data=True)):
                        self.scene_graph.add_edge(u, locations[0], **data)
                    for u, v, data in list(self.scene_graph.in_edges(loc, data=True)):
                        self.scene_graph.add_edge(u, locations[0], **data)
                    self.scene_graph.remove_node(loc)
        
        # Remove isolated nodes that aren't important entities
        for node in list(nx.isolates(self.scene_graph)):
            if not self.is_important_element(node, 'entity'):
                self.scene_graph.remove_node(node)
    
    def export_graph(self, format: str = 'json') -> str:
        """Export the graph in JSON format.
        
        Returns:
            str: The exported graph data in JSON format
        """
        # Export as JSON with all metadata
        data = {
            'nodes': [
                {
                    'id': node,
                    'type': data.get('type', 'unknown'),
                    'state': data.get('state', ''),
                    'action': data.get('action', '')
                }
                for node, data in self.scene_graph.nodes(data=True)
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'type': data.get('type', 'unknown'),
                    'relationship': data.get('relationship', '')
                }
                for u, v, data in self.scene_graph.edges(data=True)
            ],
            'metadata': {
                'node_count': len(self.scene_graph.nodes),
                'edge_count': len(self.scene_graph.edges),
                'export_time': datetime.now().isoformat(),
                'entities': list(self.main_entities),
                'locations': {k: {'prep': v[0], 'location': v[1]} for k, v in self.locations.items()},
                'states': self.states,
                'actions': self.actions
            }
        }
        return json.dumps(data, indent=2)
    
    def get_graph_data(self) -> Dict:
        """Get the current scene graph data for visualization."""
        data = {
            'nodes': [
                {
                    'id': node,
                    'type': data.get('type', 'unknown'),
                    'state': data.get('state', ''),
                    'action': data.get('action', '')
                }
                for node, data in self.scene_graph.nodes(data=True)
            ],
            'edges': [
                {
                    'from': u,
                    'to': v,
                    'type': data.get('type', 'unknown'),
                    'relationship': data.get('relationship', '')
                }
                for u, v, data in self.scene_graph.edges(data=True)
            ]
        }
        return data
    
    def reset_graph(self):
        """Reset the scene graph to start fresh."""
        self.scene_graph = nx.DiGraph()
        self.main_entities = set()
        self.locations = {}
        self.states = {}
        self.actions = {} 