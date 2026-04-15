"""
🧪 TEST: knowledge_ingester.py
==============================

Tests unitarios básicos para el módulo de ingesta de conocimiento externo.

Ejecución:
  python test_knowledge_ingester.py
"""

import os
import json
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Importar funciones del módulo
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from knowledge_ingester import (
    extract_topics_from_note,
    validate_and_extract_knowledge,
    enrich_note_with_references,
    annotate_graph_with_sources,
)


class TestExtractTopics(unittest.TestCase):
    """Test de extracción de temas"""
    
    def test_extract_topics_basic(self):
        """Test: Extrae palabras del título"""
        content = """
# Expansión del Universo

El universo se expande constantemente...
        """
        topics = extract_topics_from_note(content, max_topics=5)
        self.assertIn("Expansión", topics)
        self.assertIn("Universo", topics)
    
    def test_extract_topics_with_quotes(self):
        """Test: Extrae frases entre comillas"""
        content = '# Tema\n\nEsta es una "frase importante" que debe extraerse.'
        topics = extract_topics_from_note(content)
        self.assertIn("frase importante", topics)
    
    def test_extract_topics_empty(self):
        """Test: Maneja contenido vacío"""
        topics = extract_topics_from_note("")
        self.assertEqual(len(topics), 0)
    
    def test_extract_topics_limit(self):
        """Test: Respeta límite de temas"""
        content = "# Uno dos tres cuatro cinco seis siete ocho"
        topics = extract_topics_from_note(content, max_topics=3)
        self.assertLessEqual(len(topics), 3)


class TestValidateKnowledge(unittest.TestCase):
    """Test de validación de conocimiento"""
    
    def test_validate_empty_results(self):
        """Test: Maneja resultados vacíos"""
        validated = validate_and_extract_knowledge([], "query")
        
        self.assertIsInstance(validated, dict)
        self.assertEqual(len(validated["wikipedia"]), 0)
        self.assertEqual(len(validated["arxiv"]), 0)
    
    def test_validate_without_embeddings(self):
        """Test: Funciona sin embeddings disponibles"""
        results = [
            {
                "source": "Wikipedia",
                "title": "Test",
                "url": "http://example.com",
                "summary": "Test content",
                "relevance_score": 0.8
            }
        ]
        validated = validate_and_extract_knowledge(results, "test query")
        
        # Si no hay embeddings, debe aceptar todo
        self.assertIsInstance(validated, dict)


class TestEnrichNote(unittest.TestCase):
    """Test de enriquecimiento de notas"""
    
    def setUp(self):
        """Crear directorio temporal para tests"""
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_note.md")
        
        # Crear nota de prueba
        with open(self.test_file, 'w') as f:
            f.write("# Test Note\n\nContenido de prueba.")
    
    def tearDown(self):
        """Limpiar directorio temporal"""
        shutil.rmtree(self.test_dir)
    
    def test_enrich_adds_section(self):
        """Test: Agrega sección de fuentes"""
        knowledge = {
            "wikipedia": [
                {
                    "source": "Wikipedia",
                    "title": "Test Article",
                    "url": "http://example.com",
                    "summary": "Test summary",
                    "similarity_score": 0.8
                }
            ],
            "arxiv": [],
            "pubmed": [],
            "news": []
        }
        
        result = enrich_note_with_references(self.test_file, knowledge)
        
        # Verificar que se agregó la sección
        with open(self.test_file, 'r') as f:
            content = f.read()
        
        self.assertIn("## Fuentes Externas", content)
        self.assertTrue(result)
    
    def test_enrich_no_duplicate_section(self):
        """Test: No agrega duplicadas de fuentes"""
        # Crear nota ya enriquecida
        with open(self.test_file, 'w') as f:
            f.write("# Test\n\n## Fuentes Externas\n\nYa tiene fuentes.")
        
        knowledge = {
            "wikipedia": [],
            "arxiv": [],
            "pubmed": [],
            "news": []
        }
        
        result = enrich_note_with_references(self.test_file, knowledge)
        
        # No debe cambiar
        self.assertFalse(result)


class TestAnnotateGraph(unittest.TestCase):
    """Test de anotación del grafo"""
    
    def test_annotate_graph_basic(self):
        """Test: Anota grafo con fuentes"""
        grafo = {
            "nodos": {},
            "enlaces": {}
        }
        
        sources = {
            "wikipedia": [
                {
                    "source": "Wikipedia",
                    "url": "http://example.com",
                    "title": "Test",
                    "combined_score": 0.8
                }
            ],
            "arxiv": [],
            "pubmed": [],
            "news": []
        }
        
        result = annotate_graph_with_sources(grafo, "test.md", sources)
        
        self.assertTrue(result)
        self.assertIn("fuentes", grafo)
        self.assertIn("test.md", grafo["fuentes"])
        self.assertEqual(len(grafo["fuentes"]["test.md"]), 1)
    
    def test_annotate_graph_empty_sources(self):
        """Test: Maneja fuentes vacías"""
        grafo = {"nodos": {}, "enlaces": {}}
        sources = {
            "wikipedia": [],
            "arxiv": [],
            "pubmed": [],
            "news": []
        }
        
        result = annotate_graph_with_sources(grafo, "test.md", sources)
        
        self.assertFalse(result)


class TestIntegration(unittest.TestCase):
    """Tests de integración"""
    
    def setUp(self):
        """Preparar entorno de test"""
        self.test_dir = tempfile.mkdtemp()
        self.notas_dir = os.path.join(self.test_dir, "notas")
        os.makedirs(self.notas_dir)
    
    def tearDown(self):
        """Limpiar"""
        shutil.rmtree(self.test_dir)
    
    def test_full_pipeline(self):
        """Test: Pipeline completo de investigación"""
        # 1. Crear nota de prueba
        nota_path = os.path.join(self.notas_dir, "test_topic.md")
        with open(nota_path, 'w') as f:
            f.write("# Test Topic\n\nContenido sobre el tema.")
        
        # 2. Extraer temas
        with open(nota_path, 'r') as f:
            content = f.read()
        topics = extract_topics_from_note(content)
        
        self.assertGreater(len(topics), 0)
        
        # 3. Validar (sin resultados, pero no debe fallar)
        validated = validate_and_extract_knowledge([], "test query")
        self.assertIsNotNone(validated)


# ==================== SUITE DE TESTS ====================

def run_tests():
    """Ejecuta suite de tests"""
    print("\n" + "="*60)
    print("🧪 EJECUTANDO TESTS - knowledge_ingester")
    print("="*60 + "\n")
    
    # Crear suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Agregar tests
    suite.addTests(loader.loadTestsFromTestCase(TestExtractTopics))
    suite.addTests(loader.loadTestsFromTestCase(TestValidateKnowledge))
    suite.addTests(loader.loadTestsFromTestCase(TestEnrichNote))
    suite.addTests(loader.loadTestsFromTestCase(TestAnnotateGraph))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegration))
    
    # Ejecutar
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*60)
    if result.wasSuccessful():
        print("✅ TODOS LOS TESTS PASARON")
    else:
        print(f"❌ {len(result.failures)} fallos, {len(result.errors)} errores")
    print("="*60 + "\n")
    
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(run_tests())
