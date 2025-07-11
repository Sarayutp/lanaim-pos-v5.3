"""
Shopping Cart Enhanced System - Phase 2
Advanced cart management with persistence, validation, and real-time updates
"""

from flask import Blueprint, request, jsonify, session
from models import db, Menu, MenuOptionItem, DeliveryZone, Order, OrderItem
from datetime import datetime, timedelta
import json

# Create cart blueprint
cart_bp = Blueprint('cart', __name__, url_prefix='/api/cart')

class CartManager:
    """Enhanced cart management with persistence and validation"""
    
    @staticmethod
    def get_cart():
        """Get current cart from session"""
        return session.get('cart', {
            'items': [],
            'zone_id': None,
            'subtotal': 0,
            'delivery_fee': 0,
            'total': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        })
    
    @staticmethod
    def save_cart(cart):
        """Save cart to session with timestamp"""
        cart['updated_at'] = datetime.now().isoformat()
        session['cart'] = cart
        session.permanent = True  # Make session persistent
    
    @staticmethod
    def validate_menu_item(menu_id):
        """Validate menu item exists and is active"""
        menu = db.session.get(Menu, menu_id)
        if not menu or not menu.is_active:
            return None, "Menu item not found or not available"
        return menu, None
    
    @staticmethod
    def validate_options(options):
        """Validate menu options exist and are active"""
        validated_options = []
        total_option_price = 0
        
        for option in options:
            option_item = db.session.get(MenuOptionItem, option.get('id'))
            if not option_item or not option_item.is_active:
                return None, 0, f"Option {option.get('id')} not found or not available"
            
            validated_option = {
                'id': option_item.id,
                'name': option_item.name,
                'price': float(option_item.additional_price),
                'group_name': option_item.option_group.name if option_item.option_group else 'Custom'
            }
            validated_options.append(validated_option)
            total_option_price += option_item.additional_price
        
        return validated_options, total_option_price, None
    
    @staticmethod
    def calculate_item_total(menu_price, options_price, quantity):
        """Calculate total price for cart item"""
        return (menu_price + options_price) * quantity
    
    @staticmethod
    def find_cart_item(cart, menu_id, options):
        """Find existing cart item with same menu and options"""
        for i, item in enumerate(cart['items']):
            if (item['menu_id'] == menu_id and 
                item.get('options', []) == options):
                return i
        return None

@cart_bp.route('/add', methods=['POST'])
def add_to_cart():
    """Enhanced add to cart with validation and smart merging"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'menu_id' not in data:
            return jsonify({'error': 'Menu ID is required'}), 400
        
        menu_id = int(data['menu_id'])
        quantity = max(1, int(data.get('quantity', 1)))
        options = data.get('options', [])
        special_instructions = data.get('special_instructions', '').strip()
        
        # Validate menu item
        menu, error = CartManager.validate_menu_item(menu_id)
        if error:
            return jsonify({'error': error}), 404
        
        # Validate options
        validated_options, options_price, error = CartManager.validate_options(options)
        if error:
            return jsonify({'error': error}), 404
        
        # Get current cart
        cart = CartManager.get_cart()
        
        # Calculate prices
        item_total = CartManager.calculate_item_total(menu.price, options_price, quantity)
        
        # Check if item already exists (same menu + options)
        existing_index = CartManager.find_cart_item(cart, menu_id, validated_options)
        
        if existing_index is not None:
            # Update existing item
            cart['items'][existing_index]['quantity'] += quantity
            cart['items'][existing_index]['total_price'] = CartManager.calculate_item_total(
                menu.price, options_price, cart['items'][existing_index]['quantity']
            )
            action = 'updated'
        else:
            # Add new item
            cart_item = {
                'id': str(datetime.now().timestamp()),  # Unique ID for frontend
                'menu_id': menu_id,
                'menu_name': menu.name,
                'menu_price': float(menu.price),
                'quantity': quantity,
                'options': validated_options,
                'options_price': float(options_price),
                'total_price': float(item_total),
                'special_instructions': special_instructions,
                'added_at': datetime.now().isoformat()
            }
            cart['items'].append(cart_item)
            action = 'added'
        
        # Recalculate cart totals
        cart = recalculate_cart_totals(cart)
        
        # Save cart
        CartManager.save_cart(cart)
        
        return jsonify({
            'success': True,
            'message': f'Item {action} to cart',
            'action': action,
            'cart_summary': {
                'items_count': len(cart['items']),
                'total_quantity': sum(item['quantity'] for item in cart['items']),
                'subtotal': cart['subtotal'],
                'total': cart['total']
            }
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid input format'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to add item to cart: {str(e)}'}), 500

@cart_bp.route('/update', methods=['PUT'])
def update_cart_item():
    """Update cart item quantity or remove item"""
    try:
        data = request.get_json()
        
        if not data or 'item_id' not in data:
            return jsonify({'error': 'Item ID is required'}), 400
        
        item_id = data['item_id']
        quantity = int(data.get('quantity', 0))
        
        cart = CartManager.get_cart()
        
        # Find item to update
        item_index = None
        for i, item in enumerate(cart['items']):
            if item['id'] == item_id:
                item_index = i
                break
        
        if item_index is None:
            return jsonify({'error': 'Item not found in cart'}), 404
        
        if quantity <= 0:
            # Remove item
            removed_item = cart['items'].pop(item_index)
            action = 'removed'
            message = f"Removed {removed_item['menu_name']} from cart"
        else:
            # Update quantity
            item = cart['items'][item_index]
            item['quantity'] = quantity
            item['total_price'] = CartManager.calculate_item_total(
                item['menu_price'], item['options_price'], quantity
            )
            action = 'updated'
            message = f"Updated {item['menu_name']} quantity to {quantity}"
        
        # Recalculate totals
        cart = recalculate_cart_totals(cart)
        
        # Save cart
        CartManager.save_cart(cart)
        
        return jsonify({
            'success': True,
            'message': message,
            'action': action,
            'cart_summary': {
                'items_count': len(cart['items']),
                'total_quantity': sum(item['quantity'] for item in cart['items']),
                'subtotal': cart['subtotal'],
                'total': cart['total']
            }
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid input format'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to update cart: {str(e)}'}), 500

@cart_bp.route('/clear', methods=['DELETE'])
def clear_cart():
    """Clear entire cart"""
    try:
        # Reset cart
        cart = {
            'items': [],
            'zone_id': None,
            'subtotal': 0,
            'delivery_fee': 0,
            'total': 0,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        CartManager.save_cart(cart)
        
        return jsonify({
            'success': True,
            'message': 'Cart cleared successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to clear cart: {str(e)}'}), 500

@cart_bp.route('/set-zone', methods=['POST'])
def set_delivery_zone():
    """Set delivery zone for cart"""
    try:
        data = request.get_json()
        
        if not data or 'zone_id' not in data:
            return jsonify({'error': 'Zone ID is required'}), 400
        
        zone_id = int(data['zone_id'])
        
        # Validate zone
        zone = db.session.get(DeliveryZone, zone_id)
        if not zone or not zone.is_active:
            return jsonify({'error': 'Delivery zone not found or not available'}), 404
        
        # Update cart
        cart = CartManager.get_cart()
        cart['zone_id'] = zone_id
        cart['zone_name'] = zone.name
        cart['delivery_fee'] = float(zone.delivery_fee)
        
        # Recalculate totals
        cart = recalculate_cart_totals(cart)
        
        # Save cart
        CartManager.save_cart(cart)
        
        return jsonify({
            'success': True,
            'message': f'Delivery zone set to {zone.name}',
            'zone': {
                'id': zone.id,
                'name': zone.name,
                'delivery_fee': float(zone.delivery_fee)
            },
            'cart_summary': {
                'subtotal': cart['subtotal'],
                'delivery_fee': cart['delivery_fee'],
                'total': cart['total']
            }
        })
        
    except ValueError as e:
        return jsonify({'error': 'Invalid zone ID format'}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to set delivery zone: {str(e)}'}), 500

@cart_bp.route('/', methods=['GET'])
def get_cart():
    """Get current cart with detailed information"""
    try:
        cart = CartManager.get_cart()
        
        # Add menu details to cart items
        enriched_items = []
        for item in cart['items']:
            menu = db.session.get(Menu, item['menu_id'])
            if menu:
                enriched_item = item.copy()
                enriched_item['menu_details'] = {
                    'category': menu.category,
                    'description': menu.description,
                    'image_url': menu.image_url,
                    'prep_time': menu.prep_time
                }
                enriched_items.append(enriched_item)
        
        cart['items'] = enriched_items
        
        # Add zone details if set
        if cart.get('zone_id'):
            zone = db.session.get(DeliveryZone, cart['zone_id'])
            if zone:
                cart['zone_details'] = {
                    'id': zone.id,
                    'name': zone.name,
                    'description': zone.description,
                    'delivery_fee': float(zone.delivery_fee)
                }
        
        return jsonify({
            'success': True,
            'cart': cart,
            'summary': {
                'items_count': len(cart['items']),
                'total_quantity': sum(item['quantity'] for item in cart['items']),
                'subtotal': cart['subtotal'],
                'delivery_fee': cart['delivery_fee'],
                'total': cart['total'],
                'estimated_prep_time': estimate_prep_time(cart['items'])
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get cart: {str(e)}'}), 500

def recalculate_cart_totals(cart):
    """Recalculate cart subtotal and total"""
    # Calculate subtotal
    subtotal = sum(item['total_price'] for item in cart['items'])
    cart['subtotal'] = float(subtotal)
    
    # Get delivery fee
    delivery_fee = cart.get('delivery_fee', 0)
    
    # Calculate total
    cart['total'] = float(subtotal + delivery_fee)
    
    return cart

def estimate_prep_time(cart_items):
    """Estimate total preparation time based on cart items"""
    if not cart_items:
        return 0
    
    total_prep_time = 0
    for item in cart_items:
        menu = db.session.get(Menu, item['menu_id'])
        if menu and menu.prep_time:
            # Add prep time weighted by quantity (but with diminishing returns)
            item_prep_time = menu.prep_time + (item['quantity'] - 1) * (menu.prep_time * 0.3)
            total_prep_time = max(total_prep_time, item_prep_time)
    
    # Add 5 minutes buffer for multiple items
    if len(cart_items) > 1:
        total_prep_time += 5
    
    return int(total_prep_time)
