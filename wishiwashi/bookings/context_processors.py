def total_items(request):
    total_items = 0
    if hasattr(request, 'session') and 'items' in request.session:
        for product_id, quantity in request.session['items'].items():
            total_items += int(quantity)

    return {'TOTAL_ITEMS': total_items}
