#!/usr/bin/env python3
"""
Test script to verify the installation is working correctly.
"""

import sys
import traceback

def test_import(module_name, optional=False):
    """Test importing a module."""
    try:
        __import__(module_name)
        print(f"✅ {module_name} - OK")
        return True
    except ImportError as e:
        if optional:
            print(f"⚠️ {module_name} - OPTIONAL (not installed)")
        else:
            print(f"❌ {module_name} - FAILED: {e}")
        return False

def test_spacy_model():
    """Test spaCy model availability."""
    try:
        import spacy
        try:
            nlp = spacy.load("en_core_web_lg")
            print("✅ spaCy large model - OK")
            return True
        except OSError:
            try:
                nlp = spacy.load("en_core_web_sm")
                print("✅ spaCy small model - OK")
                return True
            except OSError:
                print("❌ spaCy models - No models found")
                return False
    except ImportError:
        print("❌ spaCy - Not installed")
        return False

def test_scene_graph_builder():
    """Test the scene graph builder."""
    try:
        from scene_graph.hierarchical_graph_builder import HierarchicalGraphBuilder
        builder = HierarchicalGraphBuilder()
        print("✅ HierarchicalGraphBuilder - OK")
        
        # Test basic functionality
        test_caption = "A person is sitting at a desk with a computer"
        scene_graph, action_graph, object_graph = builder.update_scene_state(test_caption, 1.0)
        print("✅ Scene graph processing - OK")
        return True
    except Exception as e:
        print(f"❌ Scene graph builder - FAILED: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🧪 Testing LLM Camera Tracker Installation")
    print("=" * 50)
    
    # Core dependencies
    print("\n📦 Core Dependencies:")
    core_ok = all([
        test_import("networkx"),
        test_import("pyvis"),
        test_import("fastapi"),
        test_import("uvicorn"),
        test_import("aiohttp"),
        test_import("numpy"),
    ])
    
    # NLP dependencies
    print("\n🧠 NLP Dependencies:")
    nlp_ok = all([
        test_import("spacy"),
        test_spacy_model(),
    ])
    
    # Optional ML dependencies
    print("\n🤖 Optional ML Dependencies:")
    test_import("torch", optional=True)
    test_import("transformers", optional=True)
    
    # Test application components
    print("\n🏗️ Application Components:")
    app_ok = test_scene_graph_builder()
    
    # Summary
    print("\n" + "=" * 50)
    if core_ok and nlp_ok and app_ok:
        print("🎉 Installation test PASSED!")
        print("✅ Ready to run the demo with: ./run_demo.sh")
        return 0
    else:
        print("❌ Installation test FAILED!")
        if not core_ok:
            print("   - Core dependencies missing")
        if not nlp_ok:
            print("   - NLP dependencies missing")
        if not app_ok:
            print("   - Application components not working")
        print("💡 Try running: ./run_demo.sh --clean")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 