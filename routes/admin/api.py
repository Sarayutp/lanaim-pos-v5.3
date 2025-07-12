"""
Admin API endpoints for CRUD operations
"""
from flask import Blueprint, request, jsonify, abort
from werkzeug.exceptions import BadRequest
from sqlalchemy.exc import IntegrityError
from models import (
    db, Menu, Ingredient, DeliveryZone, 
    User, Promotion, Order, MenuOptionGroup, MenuOptionItem
)
from .auth import admin_required
import logging

# Create blueprint
admin_api_bp = Blueprint('admin_api', __name__, url_prefix='/admin/api')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_error(error, message="An error occurred"):
    """Standard error handler"""
    logger.error(f"{message}: {str(error)}")
    return jsonify({'error': message, 'details': str(error)}), 500

# ============= MENU CRUD =============

@admin_api_bp.route('/menu', methods=['GET'])
@admin_required
def get_menus():
    """Get all menu items"""
    try:
        menus = Menu.query.all()
        return jsonify([{
            'id': menu.id,
            'name': menu.name,
            'description': menu.description,
            'price': float(menu.price),
            'category': menu.category,
            'is_active': menu.is_active,
            'image_url': menu.image_url,
            'prep_time': menu.prep_time
        } for menu in menus])
    except Exception as e:
        return handle_error(e, "Failed to fetch menus")

@admin_api_bp.route('/menu/<int:menu_id>', methods=['GET'])
@admin_required
def get_menu(menu_id):
    """Get specific menu item"""
    try:
        menu = db.session.get(Menu, menu_id)
        if not menu:
            abort(404)
        
        return jsonify({
            'id': menu.id,
            'name': menu.name,
            'description': menu.description,
            'price': float(menu.price),
            'category': menu.category,
            'is_active': menu.is_active,
            'image_url': menu.image_url,
            'prep_time': menu.prep_time
        })
    except Exception as e:
        return handle_error(e, f"Failed to fetch menu {menu_id}")

@admin_api_bp.route('/menu', methods=['POST'])
@admin_required
def create_menu():
    """Create new menu item"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        # Validate required fields
        required_fields = ['name', 'price', 'category']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f"Missing required field: {field}")
        
        menu = Menu(
            name=data['name'],
            description=data.get('description', ''),
            price=float(data['price']),
            category=data['category'],
            is_active=data.get('is_active', True),
            image_url=data.get('image_url', ''),
            prep_time=data.get('prep_time', 15)
        )
        
        db.session.add(menu)
        db.session.commit()
        
        return jsonify({
            'id': menu.id,
            'message': 'Menu item created successfully'
        }), 201
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, "Failed to create menu item")

@admin_api_bp.route('/menu/<int:menu_id>', methods=['PUT'])
@admin_required
def update_menu(menu_id):
    """Update menu item"""
    try:
        menu = db.session.get(Menu, menu_id)
        if not menu:
            abort(404)
        
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        # Update fields
        if 'name' in data:
            menu.name = data['name']
        if 'description' in data:
            menu.description = data['description']
        if 'price' in data:
            menu.price = float(data['price'])
        if 'category' in data:
            menu.category = data['category']
        if 'is_active' in data:
            menu.is_active = data['is_active']
        if 'image_url' in data:
            menu.image_url = data['image_url']
        if 'prep_time' in data:
            menu.prep_time = data['prep_time']
        
        db.session.commit()
        
        return jsonify({'message': 'Menu item updated successfully'})
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to update menu {menu_id}")

@admin_api_bp.route('/menu/<int:menu_id>', methods=['DELETE'])
@admin_required
def delete_menu(menu_id):
    """Delete menu item"""
    try:
        menu = db.session.get(Menu, menu_id)
        if not menu:
            abort(404)
        
        # Soft delete by setting is_active to False
        menu.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Menu item deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to delete menu {menu_id}")

# ============= INGREDIENT CRUD =============

@admin_api_bp.route('/ingredient', methods=['GET'])
@admin_required
def get_ingredients():
    """Get all ingredients"""
    try:
        ingredients = Ingredient.query.all()
        return jsonify([{
            'id': ingredient.id,
            'name': ingredient.name,
            'stock_quantity': float(ingredient.stock_quantity),
            'unit': ingredient.unit,
            'cost_per_unit': float(ingredient.cost_per_unit),
            'low_stock_threshold': float(ingredient.low_stock_threshold),
            'supplier': ingredient.supplier
        } for ingredient in ingredients])
    except Exception as e:
        return handle_error(e, "Failed to fetch ingredients")

@admin_api_bp.route('/ingredient/<int:ingredient_id>', methods=['GET'])
@admin_required
def get_ingredient(ingredient_id):
    """Get specific ingredient"""
    try:
        ingredient = db.session.get(Ingredient, ingredient_id)
        if not ingredient:
            abort(404)
        
        return jsonify({
            'id': ingredient.id,
            'name': ingredient.name,
            'stock_quantity': float(ingredient.stock_quantity),
            'unit': ingredient.unit,
            'cost_per_unit': float(ingredient.cost_per_unit),
            'low_stock_threshold': float(ingredient.low_stock_threshold),
            'supplier': ingredient.supplier
        })
    except Exception as e:
        return handle_error(e, f"Failed to fetch ingredient {ingredient_id}")

@admin_api_bp.route('/ingredient', methods=['POST'])
@admin_required
def create_ingredient():
    """Create new ingredient"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        # Validate required fields
        required_fields = ['name', 'unit', 'cost_per_unit']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f"Missing required field: {field}")
        
        ingredient = Ingredient(
            name=data['name'],
            stock_quantity=data.get('stock_quantity', 0),
            unit=data['unit'],
            cost_per_unit=float(data['cost_per_unit']),
            low_stock_threshold=data.get('low_stock_threshold', 10),
            supplier=data.get('supplier', '')
        )
        
        db.session.add(ingredient)
        db.session.commit()
        
        return jsonify({
            'id': ingredient.id,
            'message': 'Ingredient created successfully'
        }), 201
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, "Failed to create ingredient")

@admin_api_bp.route('/ingredient/<int:ingredient_id>', methods=['PUT'])
@admin_required
def update_ingredient(ingredient_id):
    """Update ingredient"""
    try:
        ingredient = db.session.get(Ingredient, ingredient_id)
        if not ingredient:
            abort(404)
        
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        # Update fields
        if 'name' in data:
            ingredient.name = data['name']
        if 'stock_quantity' in data:
            ingredient.stock_quantity = float(data['stock_quantity'])
        if 'unit' in data:
            ingredient.unit = data['unit']
        if 'cost_per_unit' in data:
            ingredient.cost_per_unit = float(data['cost_per_unit'])
        if 'low_stock_threshold' in data:
            ingredient.low_stock_threshold = float(data['low_stock_threshold'])
        if 'supplier' in data:
            ingredient.supplier = data['supplier']
        
        db.session.commit()
        
        return jsonify({'message': 'Ingredient updated successfully'})
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to update ingredient {ingredient_id}")

@admin_api_bp.route('/ingredient/<int:ingredient_id>', methods=['DELETE'])
@admin_required
def delete_ingredient(ingredient_id):
    """Delete ingredient"""
    try:
        ingredient = db.session.get(Ingredient, ingredient_id)
        if not ingredient:
            abort(404)
        
        db.session.delete(ingredient)
        db.session.commit()
        
        return jsonify({'message': 'Ingredient deleted successfully'})
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Cannot delete ingredient: it is being used in menu items'}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to delete ingredient {ingredient_id}")

# ============= DELIVERY ZONE CRUD =============

@admin_api_bp.route('/zone', methods=['GET'])
@admin_required
def get_zones():
    """Get all delivery zones"""
    try:
        zones = DeliveryZone.query.all()
        return jsonify([{
            'id': zone.id,
            'name': zone.name,
            'delivery_fee': float(zone.delivery_fee),
            'is_active': zone.is_active,
            'description': zone.description
        } for zone in zones])
    except Exception as e:
        return handle_error(e, "Failed to fetch delivery zones")

@admin_api_bp.route('/zone/<int:zone_id>', methods=['GET'])
@admin_required
def get_zone(zone_id):
    """Get specific delivery zone"""
    try:
        zone = db.session.get(DeliveryZone, zone_id)
        if not zone:
            abort(404)
        
        return jsonify({
            'id': zone.id,
            'name': zone.name,
            'delivery_fee': float(zone.delivery_fee),
            'is_active': zone.is_active,
            'description': zone.description
        })
    except Exception as e:
        return handle_error(e, f"Failed to fetch delivery zone {zone_id}")

# ============= TOPPING MANAGEMENT CRUD =============

@admin_api_bp.route('/menu/<int:menu_id>/option-groups', methods=['GET'])
@admin_required
def get_menu_option_groups(menu_id):
    """Get all option groups for a menu"""
    try:
        groups = MenuOptionGroup.query.filter_by(menu_id=menu_id, is_active=True).all()
        return jsonify([{
            'id': group.id,
            'name': group.name,
            'is_required': group.is_required,
            'is_multiple': group.is_multiple,
            'options': [{
                'id': option.id,
                'name': option.name,
                'additional_price': float(option.additional_price),
                'is_active': option.is_active
            } for option in group.options if option.is_active]
        } for group in groups])
    except Exception as e:
        return handle_error(e, f"Failed to fetch option groups for menu {menu_id}")

@admin_api_bp.route('/menu/<int:menu_id>/option-groups', methods=['POST'])
@admin_required
def create_option_group(menu_id):
    """Create new option group for menu"""
    try:
        data = request.get_json()
        
        group = MenuOptionGroup(
            menu_id=menu_id,
            name=data.get('name'),
            is_required=data.get('is_required', False),
            is_multiple=data.get('is_multiple', False)
        )
        
        db.session.add(group)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'เพิ่มกลุ่มตัวเลือก "{group.name}" เรียบร้อยแล้ว',
            'group': {
                'id': group.id,
                'name': group.name,
                'is_required': group.is_required,
                'is_multiple': group.is_multiple
            }
        })
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to create option group for menu {menu_id}")

@admin_api_bp.route('/option-groups/<int:group_id>', methods=['PUT'])
@admin_required
def update_option_group(group_id):
    """Update option group"""
    try:
        group = MenuOptionGroup.query.get_or_404(group_id)
        data = request.get_json()
        
        group.name = data.get('name', group.name)
        group.is_required = data.get('is_required', group.is_required)
        group.is_multiple = data.get('is_multiple', group.is_multiple)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'แก้ไขกลุ่มตัวเลือก "{group.name}" เรียบร้อยแล้ว'
        })
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to update option group {group_id}")

@admin_api_bp.route('/option-groups/<int:group_id>', methods=['DELETE'])
@admin_required
def delete_option_group(group_id):
    """Delete option group"""
    try:
        group = MenuOptionGroup.query.get_or_404(group_id)
        
        group.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'ลบกลุ่มตัวเลือก "{group.name}" เรียบร้อยแล้ว'
        })
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to delete option group {group_id}")

@admin_api_bp.route('/option-groups/<int:group_id>/options', methods=['POST'])
@admin_required
def create_option_item(group_id):
    """Create new option item"""
    try:
        data = request.get_json()
        
        option = MenuOptionItem(
            group_id=group_id,
            name=data.get('name'),
            additional_price=float(data.get('additional_price', 0))
        )
        
        db.session.add(option)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'เพิ่มตัวเลือก "{option.name}" เรียบร้อยแล้ว',
            'option': {
                'id': option.id,
                'name': option.name,
                'additional_price': float(option.additional_price),
                'is_active': option.is_active
            }
        })
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to create option item for group {group_id}")

@admin_api_bp.route('/options/<int:option_id>', methods=['GET'])
@admin_required
def get_option_item(option_id):
    """Get single option item"""
    try:
        option = MenuOptionItem.query.get_or_404(option_id)
        
        return jsonify({
            'success': True,
            'option': {
                'id': option.id,
                'name': option.name,
                'additional_price': float(option.additional_price),
                'is_active': option.is_active,
                'group_id': option.group_id
            }
        })
    except Exception as e:
        return handle_error(e, f"Failed to fetch option item {option_id}")

@admin_api_bp.route('/options/<int:option_id>', methods=['PUT'])
@admin_required
def update_option_item(option_id):
    """Update option item"""
    try:
        option = MenuOptionItem.query.get_or_404(option_id)
        data = request.get_json()
        
        option.name = data.get('name', option.name)
        option.additional_price = float(data.get('additional_price', option.additional_price))
        
        # Handle toggle functionality
        if 'is_active' in data:
            if data['is_active'] is None:
                option.is_active = not option.is_active  # Toggle
            else:
                option.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'แก้ไขตัวเลือก "{option.name}" เรียบร้อยแล้ว'
        })
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to update option item {option_id}")

@admin_api_bp.route('/options/<int:option_id>', methods=['DELETE'])
@admin_required
def delete_option_item(option_id):
    """Delete option item"""
    try:
        option = MenuOptionItem.query.get_or_404(option_id)
        
        option.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'ลบตัวเลือก "{option.name}" เรียบร้อยแล้ว'
        })
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to delete option item {option_id}")

@admin_api_bp.route('/zone', methods=['POST'])
@admin_required
def create_zone():
    """Create new delivery zone"""
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        # Validate required fields
        required_fields = ['name', 'delivery_fee']
        for field in required_fields:
            if field not in data:
                raise BadRequest(f"Missing required field: {field}")
        
        zone = DeliveryZone(
            name=data['name'],
            delivery_fee=float(data['delivery_fee']),
            is_active=data.get('is_active', True),
            description=data.get('description', '')
        )
        
        db.session.add(zone)
        db.session.commit()
        
        return jsonify({
            'id': zone.id,
            'message': 'Delivery zone created successfully'
        }), 201
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, "Failed to create delivery zone")

@admin_api_bp.route('/zone/<int:zone_id>', methods=['PUT'])
@admin_required
def update_zone(zone_id):
    """Update delivery zone"""
    try:
        zone = db.session.get(DeliveryZone, zone_id)
        if not zone:
            abort(404)
        
        data = request.get_json()
        if not data:
            raise BadRequest("No data provided")
        
        # Update fields
        if 'name' in data:
            zone.name = data['name']
        if 'delivery_fee' in data:
            zone.delivery_fee = float(data['delivery_fee'])
        if 'is_active' in data:
            zone.is_active = data['is_active']
        if 'description' in data:
            zone.description = data['description']
        
        db.session.commit()
        
        return jsonify({'message': 'Delivery zone updated successfully'})
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to update delivery zone {zone_id}")

@admin_api_bp.route('/zone/<int:zone_id>', methods=['DELETE'])
@admin_required
def delete_zone(zone_id):
    """Delete delivery zone"""
    try:
        zone = db.session.get(DeliveryZone, zone_id)
        if not zone:
            abort(404)
        
        # Soft delete by setting is_active to False
        zone.is_active = False
        db.session.commit()
        
        return jsonify({'message': 'Delivery zone deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        return handle_error(e, f"Failed to delete delivery zone {zone_id}")

# ============= BULK OPERATIONS =============

@admin_api_bp.route('/menu/bulk-update', methods=['PUT'])
@admin_required
def bulk_update_menus():
    """Bulk update menu items"""
    try:
        data = request.get_json()
        if not data or 'items' not in data:
            raise BadRequest("No items provided")
        
        updated_count = 0
        for item_data in data['items']:
            if 'id' not in item_data:
                continue
                
            menu = db.session.get(Menu, item_data['id'])
            if not menu:
                continue
            
            # Update fields
            for field in ['name', 'description', 'price', 'category', 'is_active']:
                if field in item_data:
                    setattr(menu, field, item_data[field])
            
            updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully updated {updated_count} menu items'
        })
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, "Failed to bulk update menu items")

@admin_api_bp.route('/ingredient/bulk-update', methods=['PUT'])
@admin_required
def bulk_update_ingredients():
    """Bulk update ingredients"""
    try:
        data = request.get_json()
        if not data or 'items' not in data:
            raise BadRequest("No items provided")
        
        updated_count = 0
        for item_data in data['items']:
            if 'id' not in item_data:
                continue
                
            ingredient = db.session.get(Ingredient, item_data['id'])
            if not ingredient:
                continue
            
            # Update fields
            for field in ['name', 'stock_quantity', 'unit', 'cost_per_unit', 'low_stock_threshold', 'supplier']:
                if field in item_data:
                    setattr(ingredient, field, item_data[field])
            
            updated_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': f'Successfully updated {updated_count} ingredients'
        })
        
    except BadRequest as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return handle_error(e, "Failed to bulk update ingredients")

# ============= UTILITY ENDPOINTS =============

@admin_api_bp.route('/categories', methods=['GET'])
@admin_required
def get_categories():
    """Get all menu categories"""
    try:
        # Get unique categories from Menu table
        categories = db.session.query(Menu.category).distinct().all()
        category_list = [cat[0] for cat in categories if cat[0]]
        
        return jsonify(category_list)
    except Exception as e:
        return handle_error(e, "Failed to fetch categories")

@admin_api_bp.route('/low-stock', methods=['GET'])
@admin_required
def get_low_stock_items():
    """Get ingredients with low stock"""
    try:
        low_stock_items = Ingredient.query.filter(
            Ingredient.stock_quantity <= Ingredient.low_stock_threshold
        ).all()
        
        return jsonify([{
            'id': item.id,
            'name': item.name,
            'stock_quantity': float(item.stock_quantity),
            'low_stock_threshold': float(item.low_stock_threshold),
            'unit': item.unit
        } for item in low_stock_items])
    except Exception as e:
        return handle_error(e, "Failed to fetch low stock items")
