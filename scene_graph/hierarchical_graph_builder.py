from typing import Dict, List, Tuple, Optional, Set
import networkx as nx
from datetime import datetime
import numpy as np
from collections import deque

# Core imports that should always work
try:
    import spacy
    HAS_SPACY = True
except ImportError:
    print("Warning: spaCy not available. Text processing will be limited.")
    HAS_SPACY = False
    spacy = None

# Optional ML imports with fallbacks
try:
    from gensim.models import Word2Vec
    from gensim.models.doc2vec import Doc2Vec, TaggedDocument
    HAS_GENSIM = True
except ImportError:
    print("Warning: Gensim not available. Using basic embeddings.")
    HAS_GENSIM = False
    Word2Vec = None
    Doc2Vec = None
    TaggedDocument = None

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    print("Warning: transformers library not available. Using fallback classification.")
    HAS_TRANSFORMERS = False
    pipeline = None

# Try to import torch for advanced features
try:
    import torch
    HAS_TORCH = True
except ImportError:
    print("Warning: PyTorch not available. Some features may be limited.")
    HAS_TORCH = False
    torch = None

class HierarchicalGraphBuilder:
    def __init__(self, context_window_size: int = 5):
        """Initialize the hierarchical graph builder.
        
        Args:
            context_window_size (int): Size of the temporal context window
        """
        # Initialize NLP components
        if HAS_SPACY:
            try:
                self.nlp = spacy.load("en_core_web_lg")
            except OSError:
                try:
                    self.nlp = spacy.load("en_core_web_sm")
                    print("Warning: Using smaller spaCy model. Consider installing en_core_web_lg.")
                except OSError:
                    print("Warning: No spaCy model found. Text processing will be basic.")
                    self.nlp = None
        else:
            self.nlp = None
            
        # Initialize Doc2Vec if available
        if HAS_GENSIM:
            self.doc2vec = None  # Will be initialized with first document
        else:
            self.doc2vec = None
        
        # Initialize zero-shot classifier if available
        self.has_transformers = HAS_TRANSFORMERS
        # Disable transformers in Docker to avoid large model downloads
        import os
        disable_transformers = os.getenv('DISABLE_TRANSFORMERS', 'false').lower() == 'true'
        
        if HAS_TRANSFORMERS and not disable_transformers:
            try:
                print("Initializing zero-shot classifier (this may download a model)...")
                self.zero_shot_classifier = pipeline("zero-shot-classification")
                print("Zero-shot classifier initialized successfully")
            except Exception as e:
                print(f"Warning: Could not initialize zero-shot classifier: {e}")
                self.zero_shot_classifier = None
                self.has_transformers = False
        else:
            if disable_transformers:
                print("Transformers disabled via DISABLE_TRANSFORMERS environment variable")
            self.zero_shot_classifier = None
            self.has_transformers = False
        
        # Initialize graph layers
        self.scene_graph = nx.DiGraph()  # High-level scene events
        self.action_graph = nx.DiGraph()  # Mid-level actions
        self.object_graph = nx.DiGraph()  # Low-level objects
        
        # Temporal context
        self.context_window = deque(maxlen=context_window_size)
        self.temporal_edges = []
        
        # Entity memory
        self.entity_embeddings = {}  # Store entity embeddings
        self.entity_confidence = {}  # Track confidence scores
        
        # Initialize relationship types with confidence thresholds
        self.relationship_types = {
            'temporal': 0.5,
            'spatial': 0.3,
            'causal': 0.6,
            'interaction': 0.4
        }

    def _initialize_doc2vec(self, text: str):
        """Initialize Doc2Vec model with first document."""
        if not HAS_GENSIM or not self.nlp:
            return
            
        if self.doc2vec is None:
            # Tokenize text
            tokens = [token.text.lower() for token in self.nlp(text) if not token.is_stop and not token.is_punct]
            # Create and train Doc2Vec model
            documents = [TaggedDocument(tokens, [0])]
            self.doc2vec = Doc2Vec(documents, vector_size=100, window=5, min_count=1, workers=4)

    def _embed_text(self, text: str) -> np.ndarray:
        """Generate embeddings for text using Doc2Vec or fallback."""
        if HAS_GENSIM and self.nlp:
            self._initialize_doc2vec(text)
            if self.doc2vec:
                tokens = [token.text.lower() for token in self.nlp(text) if not token.is_stop and not token.is_punct]
                return self.doc2vec.infer_vector(tokens)
        
        # Fallback to simple hash-based embedding
        words = text.lower().split()
        # Create a simple hash-based embedding
        embedding = np.zeros(100)
        for i, word in enumerate(words[:100]):
            hash_val = hash(word) % 100
            embedding[hash_val] += 1.0 / (i + 1)  # Weight by position
        
        # Normalize
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding

    def _classify_entity_importance(self, entity: str, context: str) -> float:
        """Determine entity importance using zero-shot classification or fallback heuristics."""
        if self.zero_shot_classifier:
            try:
                candidate_labels = ["important", "background", "irrelevant"]
                result = self.zero_shot_classifier(
                    context,
                    candidate_labels,
                    hypothesis_template="This entity is {}."
                )
                return result['scores'][result['labels'].index("important")]
            except Exception as e:
                print(f"Warning: Zero-shot classification failed: {e}. Using fallback.")
        
        # Fallback heuristic classification
        entity_lower = entity.lower()
        context_lower = context.lower()
        
        # High importance keywords
        high_importance = ['person', 'man', 'woman', 'child', 'people', 'face', 'hand', 'eye']
        # Medium importance keywords  
        medium_importance = ['desk', 'table', 'chair', 'computer', 'laptop', 'screen', 'mug', 'coffee', 'shirt', 'object', 'item', 'thing', 'device', 'tool', 'furniture']
        # Low importance keywords
        low_importance = ['background', 'wall', 'floor', 'ceiling', 'shadow']
        
        # Check entity type
        for keyword in high_importance:
            if keyword in entity_lower:
                return 0.8
        
        for keyword in medium_importance:
            if keyword in entity_lower:
                return 0.6
                
        for keyword in low_importance:
            if keyword in entity_lower:
                return 0.3
        
        # Check context frequency (entities mentioned more often are likely more important)
        entity_count = context_lower.count(entity_lower)
        if entity_count > 2:
            return 0.7
        elif entity_count > 1:
            return 0.5
        else:
            return 0.4

    def _extract_scene_elements(self, caption: str) -> Dict:
        """Extract hierarchical scene elements from the caption."""
        if not self.nlp:
            # Fallback extraction without spaCy
            return self._extract_scene_elements_fallback(caption)
            
        doc = self.nlp(caption)
        
        elements = {
            'scene': {
                'events': [],
                'transitions': [],
                'confidence': []
            },
            'actions': {
                'interactions': [],
                'movements': [],
                'confidence': []
            },
            'objects': {
                'entities': [],
                'states': [],
                'confidence': []
            }
        }
        
        # Extract events and transitions (high-level)
        for sent in doc.sents:
            # Identify main events
            main_verbs = [token for token in sent if token.pos_ == "VERB" and token.dep_ == "ROOT"]
            for verb in main_verbs:
                event = self._extract_event(verb)
                elements['scene']['events'].append(event)
                elements['scene']['confidence'].append(self._calculate_confidence(event))
        
        # Extract actions and interactions (mid-level)
        for token in doc:
            if token.pos_ == "VERB":
                action = self._extract_action(token)
                if self._is_interaction(action):
                    elements['actions']['interactions'].append(action)
                else:
                    elements['actions']['movements'].append(action)
                elements['actions']['confidence'].append(self._calculate_confidence(action))
        
        # Extract objects and states (low-level)
        # First, extract named entities
        for ent in doc.ents:
            if ent.label_ in ["PERSON", "ORG", "GPE", "OBJECT"]:
                elements['objects']['entities'].append({
                    'text': ent.text,
                    'label': ent.label_,
                    'embedding': self._embed_text(ent.text)
                })
                elements['objects']['confidence'].append(
                    self._classify_entity_importance(ent.text, caption)
                )
        
        # Also extract important nouns even if they're not named entities
        important_objects = {
            'person', 'people', 'man', 'woman', 'child', 'student', 'teacher',
            'desk', 'table', 'chair', 'computer', 'laptop', 'screen',
            'phone', 'book', 'paper', 'document', 'window', 'door',
            'keyboard', 'mouse', 'camera', 'mug', 'coffee', 'shirt'
        }
        
        for token in doc:
            if token.pos_ == "NOUN" and token.text.lower() in important_objects:
                # Avoid duplicates from named entities
                already_added = any(ent['text'].lower() == token.text.lower() 
                                  for ent in elements['objects']['entities'])
                if not already_added:
                    elements['objects']['entities'].append({
                        'text': token.text,
                        'label': 'OBJECT',
                        'embedding': self._embed_text(token.text)
                    })
                    elements['objects']['confidence'].append(
                        self._classify_entity_importance(token.text, caption)
                    )
        
        return elements

    def _extract_scene_elements_fallback(self, caption: str) -> Dict:
        """Fallback scene element extraction without spaCy."""
        elements = {
            'scene': {
                'events': [],
                'transitions': [],
                'confidence': []
            },
            'actions': {
                'interactions': [],
                'movements': [],
                'confidence': []
            },
            'objects': {
                'entities': [],
                'states': [],
                'confidence': []
            }
        }
        
        # Simple word-based extraction
        words = caption.lower().split()
        
        # Common action words
        action_words = ['walking', 'sitting', 'standing', 'holding', 'looking', 'moving', 'talking']
        # Common object words
        object_words = ['person', 'man', 'woman', 'child', 'table', 'chair', 'book', 'phone', 'computer']
        
        for word in words:
            if word in action_words:
                action = {'verb': word, 'agent': None, 'target': None, 'manner': None}
                elements['actions']['movements'].append(action)
                elements['actions']['confidence'].append(0.5)
            
            if word in object_words:
                entity = {
                    'text': word,
                    'label': 'ENTITY',
                    'embedding': self._embed_text(word)
                }
                elements['objects']['entities'].append(entity)
                elements['objects']['confidence'].append(0.6)
        
        return elements

    def _extract_event(self, verb_token) -> Dict:
        """Extract event information from a verb token."""
        event = {
            'action': verb_token.text,
            'subject': None,
            'object': None,
            'time': None,
            'location': None
        }
        
        # Extract subject
        for child in verb_token.children:
            if child.dep_ == "nsubj":
                event['subject'] = child.text
            elif child.dep_ == "dobj":
                event['object'] = child.text
            elif child.dep_ == "prep" and child.text.lower() in ["in", "at", "on"]:
                for loc in child.children:
                    if loc.dep_ == "pobj":
                        event['location'] = loc.text
        
        return event

    def _extract_action(self, verb_token) -> Dict:
        """Extract action information from a verb token."""
        return {
            'verb': verb_token.text,
            'agent': next((child.text for child in verb_token.children if child.dep_ == "nsubj"), None),
            'target': next((child.text for child in verb_token.children if child.dep_ == "dobj"), None),
            'manner': next((child.text for child in verb_token.children if child.dep_ == "advmod"), None)
        }

    def _is_interaction(self, action: Dict) -> bool:
        """Determine if an action represents an interaction between entities."""
        return action['agent'] is not None and action['target'] is not None

    def _calculate_confidence(self, element: Dict) -> float:
        """Calculate confidence score for an extracted element."""
        # Calculate confidence based on:
        # - Completeness of information
        # - Semantic similarity with context
        # - Entity recognition confidence
        
        # Check completeness
        completeness = sum(1 for v in element.values() if v is not None) / len(element)
        
        # Calculate semantic similarity with context if context exists
        context_sim = 0.0
        if self.context_window:
            context_text = ' '.join([ctx['caption'] for ctx in self.context_window])
            element_text = ' '.join(str(v) for v in element.values() if v is not None)
            context_embedding = self._embed_text(context_text)
            element_embedding = self._embed_text(element_text)
            context_sim = np.dot(context_embedding, element_embedding) / (
                np.linalg.norm(context_embedding) * np.linalg.norm(element_embedding)
            )
        
        # Combine scores
        confidence = (completeness + max(context_sim, 0.5)) / 2
        return min(max(confidence, 0.0), 1.0)

    def _update_temporal_context(self, caption: str, timestamp: float):
        """Update the temporal context window."""
        self.context_window.append({
            'caption': caption,
            'timestamp': timestamp,
            'embedding': self._embed_text(caption)
        })

    def _create_temporal_edges(self):
        """Create temporal edges between related events."""
        if len(self.context_window) < 2:
            return
        
        # Get the two most recent contexts
        current = self.context_window[-1]
        previous = self.context_window[-2]
        
        # Calculate temporal relationship
        time_diff = current['timestamp'] - previous['timestamp']
        embedding_sim = np.dot(current['embedding'], previous['embedding']) / (
            np.linalg.norm(current['embedding']) * np.linalg.norm(previous['embedding'])
        )
        
        # Add temporal edge if similarity is high enough
        if embedding_sim > self.relationship_types['temporal']:
            self.temporal_edges.append({
                'from_time': previous['timestamp'],
                'to_time': current['timestamp'],
                'relationship': 'temporal_sequence',
                'confidence': float(embedding_sim)
            })

    def update_scene_state(self, caption: str, timestamp: float) -> Tuple[nx.DiGraph, nx.DiGraph, nx.DiGraph]:
        """Update the hierarchical scene graphs based on new caption."""
        # Extract scene elements
        elements = self._extract_scene_elements(caption)
        
        # Update temporal context
        self._update_temporal_context(caption, timestamp)
        self._create_temporal_edges()
        
        # Update scene graph (high-level)
        for event, conf in zip(elements['scene']['events'], elements['scene']['confidence']):
            if conf > self.relationship_types['causal']:
                self._update_scene_graph(event)
        
        # Update action graph (mid-level)
        for action, conf in zip(elements['actions']['interactions'], elements['actions']['confidence']):
            if conf > self.relationship_types['interaction']:
                self._update_action_graph(action)
        
        # Update object graph (low-level)
        for obj, conf in zip(elements['objects']['entities'], elements['objects']['confidence']):
            if conf > self.relationship_types['spatial']:
                self._update_object_graph(obj)
        
        return self.scene_graph, self.action_graph, self.object_graph

    def _update_scene_graph(self, event: Dict):
        """Update the high-level scene graph."""
        # Add event node
        event_id = f"event_{datetime.now().timestamp()}"
        self.scene_graph.add_node(event_id, **event)
        
        # Connect to related events based on temporal and causal relationships
        for prev_event in self.scene_graph.nodes():
            if self._are_events_related(event, self.scene_graph.nodes[prev_event]):
                self.scene_graph.add_edge(
                    prev_event,
                    event_id,
                    relationship='leads_to',
                    confidence=self._calculate_event_relationship_confidence(
                        event,
                        self.scene_graph.nodes[prev_event]
                    )
                )

    def _update_action_graph(self, action: Dict):
        """Update the mid-level action graph."""
        # Add action node
        action_id = f"action_{datetime.now().timestamp()}"
        self.action_graph.add_node(action_id, **action)
        
        # Connect to related actions
        for prev_action in self.action_graph.nodes():
            if self._are_actions_related(action, self.action_graph.nodes[prev_action]):
                self.action_graph.add_edge(
                    prev_action,
                    action_id,
                    relationship='follows',
                    confidence=self._calculate_action_relationship_confidence(
                        action,
                        self.action_graph.nodes[prev_action]
                    )
                )

    def _update_object_graph(self, obj: Dict):
        """Update the low-level object graph."""
        # Add or update object node
        obj_id = obj['text'].lower()
        if obj_id not in self.object_graph:
            self.object_graph.add_node(obj_id, **obj)
        else:
            # Update existing object properties
            self.object_graph.nodes[obj_id].update(obj)
        
        # Update entity memory
        self.entity_embeddings[obj_id] = obj['embedding']
        self.entity_confidence[obj_id] = self._classify_entity_importance(
            obj['text'],
            ' '.join([ctx['caption'] for ctx in self.context_window])
        )

    def _are_events_related(self, event1: Dict, event2: Dict) -> bool:
        """Determine if two events are related."""
        # Check for shared entities
        shared_entities = set(event1.values()) & set(event2.values())
        if shared_entities:
            return True
        
        # Check for temporal proximity
        if 'time' in event1 and 'time' in event2:
            time_diff = abs(event1['time'] - event2['time'])
            if time_diff < 5.0:  # 5 seconds threshold
                return True
        
        return False

    def _are_actions_related(self, action1: Dict, action2: Dict) -> bool:
        """Determine if two actions are related."""
        # Check for shared participants
        participants1 = {action1['agent'], action1['target']}
        participants2 = {action2['agent'], action2['target']}
        return bool(participants1 & participants2)

    def _calculate_event_relationship_confidence(self, event1: Dict, event2: Dict) -> float:
        """Calculate confidence score for event relationship."""
        # Convert events to text
        text1 = ' '.join(str(v) for v in event1.values() if v is not None)
        text2 = ' '.join(str(v) for v in event2.values() if v is not None)
        
        # Calculate semantic similarity
        embedding1 = self._embed_text(text1)
        embedding2 = self._embed_text(text2)
        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )
        
        return float(similarity)

    def _calculate_action_relationship_confidence(self, action1: Dict, action2: Dict) -> float:
        """Calculate confidence score for action relationship."""
        # Convert actions to text
        text1 = ' '.join(str(v) for v in action1.values() if v is not None)
        text2 = ' '.join(str(v) for v in action2.values() if v is not None)
        
        # Calculate semantic similarity
        embedding1 = self._embed_text(text1)
        embedding2 = self._embed_text(text2)
        similarity = np.dot(embedding1, embedding2) / (
            np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
        )
        
        return float(similarity)

    def get_graph_data(self) -> Dict:
        """Get the current state of all graph layers."""
        return {
            'scene_graph': self._convert_graph_to_dict(self.scene_graph),
            'action_graph': self._convert_graph_to_dict(self.action_graph),
            'object_graph': self._convert_graph_to_dict(self.object_graph),
            'temporal_edges': self.temporal_edges
        }

    def _convert_graph_to_dict(self, graph: nx.DiGraph) -> Dict:
        """Convert a NetworkX graph to a dictionary format."""
        return {
            'nodes': [
                {
                    'id': node,
                    'data': self._make_json_safe(data)
                }
                for node, data in graph.nodes(data=True)
            ],
            'edges': [
                {
                    'source': u,
                    'target': v,
                    'data': self._make_json_safe(data)
                }
                for u, v, data in graph.edges(data=True)
            ]
        }

    def _make_json_safe(self, data: Dict) -> Dict:
        """Convert data to JSON-safe format by excluding numpy arrays and other non-serializable types."""
        safe_data = {}
        for key, value in data.items():
            # Skip numpy arrays and other non-serializable types
            if key == 'embedding':
                continue  # Skip embeddings entirely
            elif hasattr(value, '__len__') and not isinstance(value, str):
                continue  # Skip arrays/lists that aren't strings
            elif value is not None:
                # Convert numpy types to Python types
                if hasattr(value, 'item'):  # numpy scalar
                    safe_data[key] = value.item()
                else:
                    safe_data[key] = value
        return safe_data

    def reset_graphs(self):
        """Reset all graph layers and context."""
        self.scene_graph = nx.DiGraph()
        self.action_graph = nx.DiGraph()
        self.object_graph = nx.DiGraph()
        self.context_window.clear()
        self.temporal_edges = []
        self.entity_embeddings = {}
        self.entity_confidence = {} 