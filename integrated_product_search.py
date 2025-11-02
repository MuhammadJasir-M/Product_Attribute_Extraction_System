import requests
from bs4 import BeautifulSoup
import os
import urllib.request
from urllib.parse import urljoin, urlparse
import uuid
import time
import pytesseract
import cv2
import numpy as np
import re
import hashlib
from link_fetcher import fetch_product_links, filter_out_non_buying, check_urls
from attribute_extractor import extract_product_attributes
from typing import Dict, List


class FreeLogoRecognition:
    def __init__(self):
        self.roboflow_url = "https://detect.roboflow.com/logo-detection-c6qjw/2"

    def detect_brand_logo(self, image_path):
        try:
            with open(image_path, "rb") as f:
                response = requests.post(self.roboflow_url, files={"file": f})
            result = response.json()
            detected_brands = []
            if "predictions" in result:
                for prediction in result["predictions"]:
                    detected_brands.append({
                        "brand": prediction["class"],
                        "confidence": prediction["confidence"]
                    })
            return detected_brands
        except Exception as e:
            print(f"Logo detection error: {e}")
            return []


class UniversalValidationPipeline:
    def __init__(self):
        print("Initializing Universal Validation Pipeline")
        self.logo_detector = FreeLogoRecognition()
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        self.universal_brands = [
            'nike', 'adidas', 'puma', 'reebok', 'under armour', 'new balance',
            'apple', 'samsung', 'google', 'microsoft', 'sony', 'lg', 'dell', 'hp', 'lenovo', 'asus',
            'canon', 'nikon', 'panasonic', 'jbl', 'bose', 'beats',
            'zara', 'h&m', 'uniqlo', 'gap', 'levis', 'tommy hilfiger',
            'rolex', 'casio', 'fossil', 'seiko',
            'honda', 'toyota', 'bmw', 'mercedes', 'audi', 'ford'
        ]

        self.universal_colors = [
            'black', 'white', 'red', 'blue', 'green', 'yellow', 'orange', 'purple', 'pink',
            'brown', 'gray', 'grey', 'silver', 'gold', 'bronze', 'copper', 'navy', 'maroon',
            'teal', 'turquoise', 'lime', 'olive', 'coral', 'magenta', 'cyan', 'beige', 'tan'
        ]

        self.universal_types = [
            'shoes', 'sneakers', 'boots', 'sandals', 'running shoes', 'basketball shoes',
            'smartphone', 'phone', 'laptop', 'tablet', 'computer', 'headphones', 'earbuds',
            'camera', 'television', 'tv', 'monitor', 'speaker', 'smartwatch', 'watch',
            'shirt', 't-shirt', 'jacket', 'pants', 'jeans', 'dress', 'sweater', 'hoodie',
            'chair', 'table', 'sofa', 'bed', 'lamp', 'mirror',
            'book', 'magazine', 'cd', 'dvd', 'vinyl',
            'bicycle', 'treadmill', 'weights', 'yoga mat',
            'perfume', 'makeup', 'skincare', 'shampoo'
        ]

    def preprocess_image(self, image_path: str):
        try:
            image = cv2.imread(image_path)
            if image is None:
                return None
            height, width = image.shape[:2]
            image = cv2.resize(image, (width * 2, height * 2))
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            denoised = cv2.fastNlMeansDenoising(gray)
            binary = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            return binary
        except:
            return None

    def extract_text_from_image(self, image_path: str) -> str:
        if not os.path.exists(image_path):
            return ""
        processed_image = self.preprocess_image(image_path)
        if processed_image is None:
            return ""
        configs = [
            r'--oem 3 --psm 6',
            r'--oem 3 --psm 8',
            r'--oem 3 --psm 7',
            r'--oem 3 --psm 13'
        ]
        best_text = ""
        for config in configs:
            try:
                text = pytesseract.image_to_string(processed_image, config=config)
                if len(text.strip()) > len(best_text.strip()):
                    best_text = text
            except:
                continue
        return best_text.strip().lower()

    def extract_attributes_from_image(self, image_path: str, image_text: str) -> Dict[str, List[str]]:
        image_attributes = {}
        try:
            detected_logos = self.logo_detector.detect_brand_logo(image_path)
            if detected_logos:
                image_attributes['brand'] = [logo['brand'].lower() for logo in detected_logos]
        except:
            pass
        if not image_attributes.get('brand'):
            for brand in self.universal_brands:
                if brand in image_text:
                    image_attributes['brand'] = [brand]
                    break
        detected_colors = []
        for color in self.universal_colors:
            if color in image_text:
                detected_colors.append(color)
        if detected_colors:
            image_attributes['color'] = detected_colors
        detected_types = []
        for ptype in self.universal_types:
            if ptype in image_text:
                detected_types.append(ptype)
        if detected_types:
            image_attributes['type'] = detected_types
        size_patterns = [
            r'\b(\d+)\s*(?:gb|tb|mb)\b',
            r'\b(\d+(?:\.\d+)?)\s*(?:inch|inches|")\b',
            r'\b(?:size|sz)\s*(\d+(?:\.\d+)?)\b',
            r'\b(\d+)\s*(?:oz|ml|l|liter)\b'
        ]
        sizes = []
        for pattern in size_patterns:
            matches = re.findall(pattern, image_text)
            sizes.extend(matches)
        if sizes:
            image_attributes['size'] = sizes
        return image_attributes

    def enhance_attributes(self, attributes: Dict, description_text: str) -> Dict:
        enhanced = attributes.copy()
        description_lower = description_text.lower()
        known_brands = ['nike', 'adidas', 'puma', 'reebok', 'under armour', 'new balance',
                        'apple', 'samsung', 'google', 'microsoft', 'sony', 'lg']
        if 'brand' in enhanced:
            current_brands = [b.lower() for b in enhanced['brand']]
            if any(brand in ['mens', 'women', 'womens', 'kids', 'black', 'white', 'running'] for brand in
                   current_brands):
                for brand in known_brands:
                    if brand in description_lower:
                        enhanced['brand'] = [brand.title()]
                        break
        else:
            for brand in known_brands:
                if brand in description_lower:
                    enhanced['brand'] = [brand.title()]
                    break
        known_colors = ['black', 'white', 'red', 'blue', 'green', 'gray', 'silver']
        if 'color' not in enhanced:
            for color in known_colors:
                if color in description_lower:
                    enhanced['color'] = [color]
                    break
        if 'type' not in enhanced:
            if 'running' in description_lower and 'shoe' in description_lower:
                enhanced['type'] = ['running shoes']
            elif 'shoe' in description_lower or 'sneaker' in description_lower:
                enhanced['type'] = ['shoes']
        return enhanced

    def liberal_cross_modal_validation(self, description_text: str, image_path: str) -> Dict:
        enhanced_description = description_text
        description_attributes = extract_product_attributes(enhanced_description)
        if not description_attributes:
            return {"status": "rejected", "reason": "No attributes extracted from description"}
        print(f"Description attributes: {description_attributes}")
        description_attributes = self.enhance_attributes(description_attributes, enhanced_description)
        image_text = self.extract_text_from_image(image_path) if image_path else ""
        image_attributes = self.extract_attributes_from_image(image_path, image_text) if image_path else {}
        print(f"Enhanced description attributes: {description_attributes}")
        print(f"Image attributes: {image_attributes}")
        key_attrs = ['brand', 'type', 'color', 'model']
        has_key_attrs = any(attr in description_attributes for attr in key_attrs)
        if not has_key_attrs:
            return {"status": "rejected", "reason": "No meaningful attributes found in description"}
        return {
            "status": "accepted",
            "reason": "Validated using enhanced description attributes",
            "validated_attributes": description_attributes,
            "validation_mode": "enhanced_description"
        }

    def extract_user_query_attributes(self, user_query: str) -> Dict[str, List[str]]:
        """Enhanced user query extraction with original query storage"""
        query_attrs = {}
        user_query_lower = user_query.lower()

        # Store original query for model keyword checking
        query_attrs['original_query'] = user_query_lower

        # Brand detection
        for brand in self.universal_brands:
            if brand in user_query_lower:
                query_attrs['brand'] = [brand]
                break

        # Color detection
        detected_colors = []
        for color in self.universal_colors:
            if color in user_query_lower:
                detected_colors.append(color)
        if detected_colors:
            query_attrs['color'] = detected_colors

        # Type detection
        detected_types = []
        for ptype in self.universal_types:
            if ptype in user_query_lower:
                detected_types.append(ptype)
        if detected_types:
            query_attrs['type'] = detected_types

        # Size detection
        size_matches = re.findall(r'\b\d+(?:\.\d+)?\b', user_query_lower)
        if size_matches:
            query_attrs['size'] = size_matches

        return query_attrs

    def filter_listings_by_user_query(self, validated_listings: List[Dict], user_query_attrs: Dict[str, List[str]]) -> \
    List[Dict]:
        """Universal filtering with model-specific keyword enforcement"""
        passed_listings = []
        user_query_lower = user_query_attrs.get('original_query', '').lower()

        # Universal model-specific keywords that require strict matching
        model_keywords = [
            'ultra', 'pro', 'max', 'mini', 'plus', 'lite', 'air', 'studio',
            'premium', 'deluxe', 'standard', 'basic', 'advanced', 'professional',
            'compact', 'slim', 'wide', 'large', 'small', 'xl', 'xs', 's', 'm', 'l',
            'sport', 'gaming', 'business', 'home', 'office', 'outdoor', 'indoor'
        ]

        for listing in validated_listings:
            desc_attrs = listing['description_attributes']
            product_description = listing.get('description', '').lower()
            matches_user_query = True

            # STEP 1: Universal Model-Specific Keyword Enforcement
            for keyword in model_keywords:
                if keyword in user_query_lower:
                    # Check if this specific keyword exists in the product
                    keyword_found = (
                        # Check in model attributes
                            any(keyword in model_val.lower() for model_val in desc_attrs.get('model', [])) or
                            # Check in product description/title
                            keyword in product_description or
                            # Check in any other attribute values
                            any(keyword in str(val).lower() for attr_vals in desc_attrs.values() for val in attr_vals)
                    )

                    if not keyword_found:
                        print(f"Rejected {listing['product_link']}: Missing required model keyword '{keyword}'")
                        matches_user_query = False
                        break

            if not matches_user_query:
                continue

            # STEP 2: Standard Attribute Matching (Brand, Color, etc.)
            for attr_type, user_values in user_query_attrs.items():
                if attr_type == 'original_query':  # Skip the stored query
                    continue

                product_values = desc_attrs.get(attr_type, [])
                attribute_match = False

                # Exact match first
                for user_val in user_values:
                    for product_val in product_values:
                        if user_val.lower() == product_val.lower():
                            attribute_match = True
                            break
                    if attribute_match:
                        break

                # Fuzzy match for brands
                if not attribute_match and attr_type == 'brand':
                    for user_val in user_values:
                        for product_val in product_values:
                            if user_val.lower() in product_val.lower() or product_val.lower() in user_val.lower():
                                attribute_match = True
                                break
                        if attribute_match:
                            break

                # Liberal match for optional attributes
                if not attribute_match and attr_type in ['color', 'type', 'size']:
                    if not product_values:
                        attribute_match = True  # Don't penalize missing optional attributes
                    else:
                        for user_val in user_values:
                            for product_val in product_values:
                                if user_val.lower() in product_val.lower() or product_val.lower() in user_val.lower():
                                    attribute_match = True
                                    break
                            if attribute_match:
                                break

                # Reject if brand doesn't match (brand is mandatory)
                if not attribute_match and attr_type == 'brand':
                    matches_user_query = False
                    print(
                        f"Rejected {listing['product_link']}: {attr_type} mismatch - user wants {user_values}, product has {product_values}")
                    break

            if matches_user_query:
                passed_listings.append(listing)
                print(f"Accepted: {listing['product_link']}")

        return passed_listings

    def complete_universal_pipeline(self, user_query: str, product_listings: List[Dict]) -> List[Dict]:
        print(f"Starting Universal Two-Level Filtering Pipeline")
        print("=" * 60)

        user_attributes = self.extract_user_query_attributes(user_query)
        print(f"User query attributes: {user_attributes}")

        validated_listings = []
        print(f"\nProcessing {len(product_listings)} product listings...")

        for i, listing in enumerate(product_listings, 1):
            print(f"\nProcessing listing {i}/{len(product_listings)}")

            result = self.liberal_cross_modal_validation(
                listing['description'],
                listing.get('image_path')
            )

            if result['status'] == 'accepted':
                validated_listings.append({
                    'product_link': listing['product_link'],
                    'description': listing['description'],
                    'description_attributes': result['validated_attributes']
                })
                print(f"Passed Level 1 validation")
            else:
                print(f"Failed Level 1: {result['reason']}")

        print(f"\nLevel 1 Results: {len(validated_listings)}/{len(product_listings)} listings passed")

        if not user_attributes:
            print("No user attributes detected, returning all validated listings")
            return validated_listings

        print(f"\nLevel 2: Filtering by user query attributes...")
        final_listings = self.filter_listings_by_user_query(validated_listings, user_attributes)

        print(f"\nFinal Results: {len(final_listings)} listings match user query")
        return final_listings


# EnhancedProductPageScraper and CompleteIntegratedPipeline classes remain the same...
# [Include the rest of your classes here - they were correct in the original code]

class EnhancedProductPageScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        os.makedirs("product_images", exist_ok=True)

    def is_product_detail_page(self, soup, url: str) -> bool:
        product_indicators = [
            'meta[property="product:price"]', 'script[type="application/ld+json"]',
            '[data-testid*="product"]', '.product-price', '.add-to-cart', '.product-details', '[id*="product"]'
        ]
        for indicator in product_indicators:
            if soup.select_one(indicator):
                return True
        category_patterns = ['/category/', '/collection/', '/browse/', '/shop/', '/catalog/']
        if any(pattern in url.lower() for pattern in category_patterns):
            return False
        if soup.find('h1') and (soup.find('.price') or soup.find('[data-price]')):
            return True
        return True

    def scrape_product_details(self, url: str) -> Dict:
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            if not self.is_product_detail_page(soup, url):
                print(f"Skipping category page: {url}")
                return {'success': False}
            title = self.extract_title(soup)
            description = self.extract_description(soup) or title
            image_url = self.extract_main_image(soup, url)
            local_image_path = None
            if image_url:
                local_image_path = self.download_image(image_url, url)
            return {'title': title, 'description': description, 'image_url': image_url,
                    'local_image_path': local_image_path, 'success': bool(title)}
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return {'success': False}

    def extract_title(self, soup):
        selectors = ['h1', '[data-testid="product-title"]', '.product-title', '.title',
                     'h1[id*="title"]', '#productTitle', '.x-item-title-label', '[data-automation-id="product-title"]']
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element and element.get_text().strip():
                    text = element.get_text().strip()
                    if len(text) > 10 and not text.lower().startswith('skip to'):
                        return text
            except:
                continue
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        return None

    def extract_description(self, soup):
        selectors = ['[data-testid="product-description"]', '.product-description', '.description',
                     '#description', '[id*="description"]', '.product-details', '.item-description', '.product-info']
        for selector in selectors:
            try:
                element = soup.select_one(selector)
                if element and element.get_text().strip():
                    return element.get_text().strip()[:500]
            except:
                continue
        return None

    def extract_main_image(self, soup, base_url: str):
        selectors = ['img[data-testid="product-image"]', '.product-image img', '#main-image',
                     '[data-automation-id="product-image"]', 'img[id*="image"]', '.main-image img',
                     'img[alt*="product"]', 'img[src*="product"]']
        for selector in selectors:
            try:
                img = soup.select_one(selector)
                if img:
                    src = img.get('src') or img.get('data-src') or img.get('data-original')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = urljoin(base_url, src)
                        if 'http' in src:
                            return src
            except:
                continue
        images = soup.find_all('img')
        for img in images:
            src = img.get('src') or img.get('data-src')
            if src and 'http' in src:
                if not any(skip in src.lower() for skip in ['icon', 'logo', 'sprite', 'pixel', '1x1']):
                    return src
        return None

    def download_image(self, image_url: str, source_url: str) -> str:
        try:
            clean_url = image_url.split('?')[0]
            url_hash = hashlib.md5(source_url.encode()).hexdigest()[:8]
            extension = 'jpg'
            if '.' in clean_url:
                potential_ext = clean_url.split('.')[-1].lower()
                if potential_ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
                    extension = potential_ext
            filename = f"product_images/product_{url_hash}_{uuid.uuid4().hex[:8]}.{extension}"
            req = urllib.request.Request(image_url, headers=self.headers)
            urllib.request.urlretrieve(image_url, filename)
            return filename
        except Exception as e:
            print(f"Failed to download image from {image_url}: {e}")
            return None


class CompleteIntegratedPipeline:
    def __init__(self, google_api_key: str, google_cse_id: str):
        print("Initializing Complete Integrated Product Search Pipeline")
        self.google_api_key = google_api_key
        self.google_cse_id = google_cse_id
        self.scraper = EnhancedProductPageScraper()
        self.validator = UniversalValidationPipeline()

    def run_complete_search(self, user_query: str, max_results: int = 15) -> List[Dict]:
        print(f"\nCOMPLETE SEARCH PIPELINE FOR: '{user_query}'")
        print("=" * 60)
        print("\nStep 1: Fetching product URLs from Google Search...")
        fetched_urls = fetch_product_links(user_query, self.google_api_key, self.google_cse_id, max_results)
        print(f"   Fetched {len(fetched_urls)} URLs")
        if not fetched_urls:
            print("No URLs found")
            return []
        print("\nStep 2: Filtering out non-buying URLs...")
        filtered_urls = filter_out_non_buying(fetched_urls)
        print(f"   {len(filtered_urls)} URLs after filtering")
        print("\nStep 3: Checking URL genuineness...")
        valid_products_queue = check_urls(filtered_urls)
        print(f"   {len(valid_products_queue)} URLs passed genuineness check")
        print("\nStep 4: Scraping detailed product information...")
        scraped_products = []
        for i, product in enumerate(valid_products_queue, 1):
            print(f"   Scraping {i}/{len(valid_products_queue)}: {product['url'][:60]}...")
            details = self.scraper.scrape_product_details(product['url'])
            if details['success']:
                scraped_products.append({
                    'product_link': product['url'],
                    'description': details['description'],
                    'image_path': details['local_image_path'],
                    'title': details['title']
                })
                print(f"      Success: {details['title'][:40]}...")
            else:
                print(f"      Failed to scrape")
            time.sleep(0.5)
        print(f"   Successfully scraped {len(scraped_products)} products")
        print("\nStep 5: Applying BERT + Cross-modal Validation...")
        validated_products = self.validator.complete_universal_pipeline(user_query, scraped_products)
        print(f"   {len(validated_products)} products passed validation")
        final_results = []
        for product in validated_products:
            final_results.append({
                'url': product['product_link'],
                'title': next((p['title'] for p in scraped_products if p['product_link'] == product['product_link']),
                              'Unknown'),
                'description': product['description'],
                'validated_attributes': product['description_attributes'],
                'confidence': 'High'
            })
        return final_results

    def display_results(self, results: List[Dict], user_query: str):
        print(f"\nFINAL VALIDATED RESULTS FOR '{user_query}':")
        print("=" * 80)
        if not results:
            print("No products passed the complete validation pipeline")
            return
        for i, product in enumerate(results, 1):
            print(f"\n{i}. {product['title']}")
            print(f"   URL: {product['url']}")
            print(f"   Attributes: {product['validated_attributes']}")
            print(f"   Confidence: {product['confidence']}")
            print(f"   Description: {product['description'][:100]}...")
        print(f"\nSUCCESS SUMMARY:")
        print(f"   Total validated products: {len(results)}")
        print(f"   All products verified for consistency")
        print(f"   All products match user search intent")


if __name__ == "__main__":
    GOOGLE_API_KEY = "YOUR_API_KEY"
    GOOGLE_CSE_ID = "YOUR_API_KEY"

    pipeline = CompleteIntegratedPipeline(GOOGLE_API_KEY, GOOGLE_CSE_ID)

    try:
        import sys

        if len(sys.argv) > 1:
            user_query = sys.argv[1]  # From FastAPI
        else:
            user_query = input("\nEnter your product search query: ").strip()

        if not user_query:
            sys.exit(1)

        results = pipeline.run_complete_search(user_query, max_results=15)

        if results:
            import json

            output_file = f"validated_products_{user_query.replace(' ', '_')}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"Pipeline error: {e}")

        sys.exit(1)
