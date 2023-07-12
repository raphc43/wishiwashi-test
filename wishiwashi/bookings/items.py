from math import ceil
from bookings.models import Item


def get_columns_of_items(num_columns=3):
    items = Item.objects.filter(
        visible=True, category__visible=True
    ).prefetch_related('category').order_by('category__name', 'name')

    items_per_column = ceil(len(items) / float(num_columns))

    columns = list()
    current_column = 0
    category_id = items[0].category.id
    for index, item in enumerate(items):
        if index and index % items_per_column == 0.0:
            current_column += 1
            # Don't split same categories over separate columns
            if category_id == item.category.id:
                columns[current_column - 1].append(item)
                continue

        try:
            columns[current_column].append(item)
        except IndexError:
            columns.insert(current_column, [])
            columns[current_column].append(item)

        category_id = item.category.id

    return columns
