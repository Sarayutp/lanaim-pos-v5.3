"""
Simple Test for Basic Functionality
Test without complex dependencies
"""

import pytest
import tempfile
import os
from datetime import datetime

# Create simple test that doesn't require complex imports
def test_basic_python_functionality():
    """Test basic Python functionality"""
    assert 1 + 1 == 2
    assert "hello".upper() == "HELLO"
    assert len([1, 2, 3]) == 3

def test_datetime_functionality():
    """Test datetime functionality"""
    now = datetime.now()
    assert isinstance(now, datetime)
    assert now.year >= 2023

def test_file_operations():
    """Test basic file operations"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("test content")
        temp_path = f.name
    
    # Read the file
    with open(temp_path, 'r') as f:
        content = f.read()
    
    assert content == "test content"
    
    # Clean up
    os.unlink(temp_path)

def test_dictionary_operations():
    """Test dictionary operations"""
    data = {"name": "test", "value": 123}
    
    assert data["name"] == "test"
    assert data.get("value") == 123
    assert data.get("missing") is None
    
    data["new_key"] = "new_value"
    assert "new_key" in data

def test_list_operations():
    """Test list operations"""
    items = [1, 2, 3]
    
    items.append(4)
    assert len(items) == 4
    assert items[-1] == 4
    
    items.remove(2)
    assert 2 not in items
    assert len(items) == 3

class TestBasicClass:
    """Test basic class functionality"""
    
    def test_class_creation(self):
        """Test creating a simple class"""
        class SimpleClass:
            def __init__(self, value):
                self.value = value
            
            def get_value(self):
                return self.value
        
        obj = SimpleClass("test")
        assert obj.value == "test"
        assert obj.get_value() == "test"
    
    def test_class_methods(self):
        """Test class methods"""
        class Calculator:
            @staticmethod
            def add(a, b):
                return a + b
            
            @classmethod
            def multiply(cls, a, b):
                return a * b
        
        assert Calculator.add(2, 3) == 5
        assert Calculator.multiply(4, 5) == 20

if __name__ == "__main__":
    # Run tests manually if executed directly
    test_basic_python_functionality()
    test_datetime_functionality()
    test_file_operations()
    test_dictionary_operations()
    test_list_operations()
    
    test_class = TestBasicClass()
    test_class.test_class_creation()
    test_class.test_class_methods()
    
    print("✅ All basic tests passed!")
