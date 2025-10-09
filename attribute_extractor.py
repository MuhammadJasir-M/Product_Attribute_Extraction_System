import torch
from transformers import BertTokenizerFast, BertForTokenClassification
from typing import List, Dict, Tuple

class ProductAttributeExtractor:
    def __init__(self, model_path="./bert_attribute_model"):
        """Initialize the production attribute extractor"""
        
        # CORRECTED: Use exact same labels as training
        self.labels = [
            "O",
            "B-BRAND", "I-BRAND",
            "B-COLOR", "I-COLOR",
            "B-SIZE", "I-SIZE",
            "B-MATERIAL", "I-MATERIAL",
            "B-MODEL", "I-MODEL",
            "B-BATTERY", "I-BATTERY",
            "B-PROCESSOR", "I-PROCESSOR",
            "B-DISPLAY_SIZE", "I-DISPLAY_SIZE",
            "B-DISPLAY_TYPE", "I-DISPLAY_TYPE",
            "B-MEMORY", "I-MEMORY",
            "B-DIMENSIONS", "I-DIMENSIONS",
            "B-AUTHOR", "I-AUTHOR",
            "B-PUBLISHER", "I-PUBLISHER",
            "B-ISBN", "I-ISBN",
            "B-EDITION", "I-EDITION",
            "B-PAGES", "I-PAGES",
            "B-SHADE", "I-SHADE",
            "B-VOLUME", "I-VOLUME",
            "B-TYPE", "I-TYPE",
            "B-CAPACITY", "I-CAPACITY",
            "B-ENERGY_RATING", "I-ENERGY_RATING",
            "B-TITLE", "I-TITLE",
            "B-YEAR", "I-YEAR",
            "B-PART_TYPE", "I-PART_TYPE",
            "B-WEIGHT", "I-WEIGHT"
        ]
        
        self.label_to_id = {label: i for i, label in enumerate(self.labels)}
        self.id_to_label = {i: label for label, i in self.label_to_id.items()}
        
        # Load model and tokenizer
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = BertTokenizerFast.from_pretrained(model_path)
        self.model = BertForTokenClassification.from_pretrained(
            model_path, 
            id2label=self.id_to_label, 
            label2id=self.label_to_id
        )
        self.model.to(self.device)
        self.model.eval()
    
    def extract_attributes(self, text: str) -> Dict[str, List[str]]:
        """Extract and organize product attributes"""
        
        tokens = text.split()
        
        # CORRECTED: Proper tokenization with word_ids
        tokenized_inputs = self.tokenizer(
            tokens, 
            is_split_into_words=True, 
            return_tensors="pt", 
            truncation=True, 
            padding="max_length", 
            max_length=128
        )
        
        # Get word_ids before converting to dict
        word_ids = tokenized_inputs.word_ids(batch_index=0)
        inputs = {k: v.to(self.device) for k, v in tokenized_inputs.items()}
        
        with torch.no_grad():
            outputs = self.model(**inputs)
        
        predictions = torch.argmax(outputs.logits, dim=2)
        
        # CORRECTED: Proper token-prediction alignment
        predicted_labels = []
        previous_word_idx = None
        for i, word_idx in enumerate(word_ids):
            if word_idx is not None and word_idx != previous_word_idx:
                if word_idx < len(tokens):
                    pred_id = predictions[0][i].item()
                    predicted_labels.append(self.id_to_label[pred_id])
                    previous_word_idx = word_idx
        
        while len(predicted_labels) < len(tokens):
            predicted_labels.append("O")
        
        # Organize into structured output
        return self._organize_attributes(tokens, predicted_labels[:len(tokens)])
    
    def _organize_attributes(self, tokens: List[str], labels: List[str]) -> Dict[str, List[str]]:
        """Organize extracted attributes into categories"""
        
        attributes = {
            "brand": [],
            "model": [],
            "type": [],
            "color": [],
            "size": [],
            "display_size": [],
            "display_type": [],
            "material": [],
            "memory": [],
            "processor": [],
            "capacity": [],
            "weight": [],
            "dimensions": [],
            "author": [],
            "publisher": [],
            "title": [],
            "shade": [],
            "volume": [],
            "battery": [],
            "year": [],
            "part_type": [],
            "energy_rating": [],
            "isbn": [],
            "edition": [],
            "pages": []
        }
        
        current_entity = []
        current_type = None
        
        for token, label in zip(tokens, labels):
            if label.startswith('B-'):
                # Save previous entity
                if current_entity and current_type:
                    self._add_to_attributes(attributes, current_type, ' '.join(current_entity))
                
                # Start new entity
                current_type = label[2:].lower()
                current_entity = [token]
                
            elif label.startswith('I-') and current_type and current_type == label[2:].lower():
                # Continue current entity
                current_entity.append(token)
                
            else:
                # End current entity
                if current_entity and current_type:
                    self._add_to_attributes(attributes, current_type, ' '.join(current_entity))
                current_entity = []
                current_type = None
        
        # Handle last entity
        if current_entity and current_type:
            self._add_to_attributes(attributes, current_type, ' '.join(current_entity))
        
        # Return only non-empty attributes
        return {k: v for k, v in attributes.items() if v}
    
    def _add_to_attributes(self, attributes: Dict, attr_type: str, value: str):
        """Add attribute value to appropriate category"""
        if attr_type in attributes:
            attributes[attr_type].append(value)

# Global instance for easy importing
extractor = ProductAttributeExtractor()

# API Functions
def extract_product_attributes(text: str) -> Dict[str, List[str]]:
    """Main API function for attribute extraction"""
    return extractor.extract_attributes(text)

def get_specific_attribute(text: str, attribute_type: str) -> List[str]:
    """Get specific attribute type"""
    attributes = extractor.extract_attributes(text)
    return attributes.get(attribute_type, [])

# Test function
def test_extractor():
    test_cases = [
        "Samsung Galaxy S25 Ultra smartphone with 6.9-inch AMOLED display and 12GB RAM",
        "Nike running shoes in black color size 10",
        "LG washing machine 7kg capacity front-load",
        "Samsung Galaxy Watch 6 Classic Black Silicone strap"
    ]
    
    for text in test_cases:
        print(f"\nInput: {text}")
        result = extract_product_attributes(text)
        print("Extracted Attributes:")
        for category, values in result.items():
            print(f"  {category}: {values}")

# Example usage
if __name__ == "__main__":
    test_extractor()
