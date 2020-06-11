import operator
from functools import reduce
from typing import Union
import json
import numpy as np
import dash
import dash_html_components as html


def set_className_entry(original_className, className_to_toggle, return_has_className=True):
    """
    Sets/unsets a className within a space separated list of classNames

    If return_has_className=True, the returned className will include exactly one of className_to_toggle.
    If return_has_className=False, the returned className will include exactly none of className_to_toggle.

    Returns:
        (str): Updated className
    """
    name_list = original_className.strip().split()

    # Remove all of className in question
    name_list = [x for x in name_list if x != className_to_toggle]

    if return_has_className:
        name_list.append(className_to_toggle)

    return " ".join(name_list)


def get_className_state(full_className, className_to_check):
    name_list = full_className.strip().split()
    return className_to_check in name_list


def generate_checklist_li_id(id):
    return {"type": "list_item",
            "id": id,
            }


def generate_checklist_ul_id(id):
    return {"type": "unordered_list",
            "id": id,
            }


def get_path_to_id_in_serialized_ul(ul: dict, obj_id: str, _upstream_path=None):
    """
    Depth first search of a dict of Plotly objects with children, returning the path to the first obj with the id obj_id

    Args:
        ul (dict):
        obj_id:  Any valid Plotly object id (str, dict)
        _upstream_path: Used for recursion.  Typically should not be defined externally

    Returns:
        (tuple): a tuple defining all steps taken in the ul children dict to get to the item, eg:
                    (index_lvl_1, key_lvl_2, ...)
    """
    _upstream_path = tuple() if not _upstream_path else _upstream_path

    for i, child in enumerate(ul):
        # Iterate on objects in children list.  These will have {'props', 'type'}, with 'props' having 'id' and
        # 'children'
        this_upstream_path = _upstream_path + (i,)
        if child['props']['id'] == obj_id:
            return this_upstream_path
        else:
            # If there are children, go deeper
            if isinstance(child['props']['children'], (tuple, list)):
                returned_from_child = get_path_to_id_in_serialized_ul(child['props']['children'],
                                                                      obj_id,
                                                                      _upstream_path=this_upstream_path + ('props',
                                                                                                           'children'))
                if returned_from_child:
                    return returned_from_child

    # Nothing found, return None
    return None


def get_by_path(obj, path):
    return reduce(operator.getitem, path, obj)


def get_leaves_below_sidebar_obj(ul_children: dict, path_to_obj: Union[str, tuple, list]):
    """
    Get all leaf nodes (Li objects without corresponding Ul) from a dict defining the the children of a Ul

    Args:
        ul_children: Children attribute of a Ul object, defined as a dictionary.  Same format as Dash passes to a
                     callback watching the "children" attribute of a Ul.
        path_to_obj: A tuple of keys and indices defining where to start within ul_children when looking for children.
                     For example:
                        (index_lvl_1, key_lvl_2, ...)
                     The same as returned by get_path_to_id_in_serialized_ul()

    Returns:
        (list): List of references to the leaves found in ul_children (if mutated in place, they will change the
                ul_children instance)
    """
    # Traverse the children of this object, returning and child Li objs that have no paired Ul or any leaves of nested
    # Uls
    if path_to_obj:
        if not isinstance(path_to_obj, (tuple, list)):
            path_to_obj = (path_to_obj,)

        start_obj = get_by_path(ul_children, path_to_obj)
    else:
        start_obj = ul_children

    to_return = []

    # Temp variables to determine which items are leaves
    lis = {}
    uls_ids = set()

    # start_obj may be pointed at a dict defining a dash component with format:
    #   {
    #       'namespace': ...,
    #       'type': ...,
    #       'props': {
    #           'children': ...,
    #       }
    #   }
    # Where we want to inspect the 'children' to see if there are any Li's without Ul's.  Or, we might be pointed
    # directly at 'children' (such as when getting input directly from a dash callback input).  Figure out which
    # situation we're in
    if 'props' in start_obj:
        path_to_obj = path_to_obj + ('props', 'children')
        start_obj = start_obj['props']['children']

    # If we have children, recurse.  Else, return this
    if isinstance(start_obj, (tuple, list)):
        for i, child in enumerate(start_obj):
            child_type = child['type']
            try:
                child_idname = child['props']['id']['id']
            except TypeError:
                # This is just a text label, not an entry that will have relevance to us here
                continue
            if child_type == 'Li':
                lis[child_idname] = child
            elif child_type == 'Ul':
                uls_ids.add(child_idname)
                to_return.extend(get_leaves_below_sidebar_obj(ul_children, path_to_obj + (i,)))
    else:
        to_return.append(start_obj)

    # Add Lis found that have no paired Uls
    to_add_to_return = [li for li_id, li in lis.items() if li_id not in uls_ids]
    to_return.extend(to_add_to_return)

    return to_return


def make_sidebar_children(data, top_item, inherited_class="", child_class="", depth=np.inf, budget_collection=None,
                          show_categories=True):
    """
    Recursively generate a hierarchical list defined by data, starting at top_item, using Ul and Li objects

    Ul and Li objects ids are defined by Dash id dicts so they can be subscribed to by a callback as a group

    For each node, we generate:
        * An Li object with children=item_name
        * (If node is a middle node with additional children) a Ul object with children=[child_nodes, built recursively]

    TODO: Originally written to be very general, the addition of budget_collection for category and amount printing in
     the sidebar makes this tightly coupled with budget_collections.  Instead of interpreting the nested dict data, we
     could get all information from the budget_collection itself instead.

    Args:
        data (dict): Dict of lists of relationships within the nested list.  For example:
                        {
                            "Item-1": ["Item-1-1", "Item-1-2", ...],
                            "Item-2": ["Item-2-1", "Item-2-2", ...],
                            "Item-1-1": ["Item-1-1-1", "Item-1-1-2", ...],
                            ...
                        }
                     Note that this does not handle repeated names (eg: Item-1-1 cannot have the same name as Item-2)
        top_item (str): The key in data that denotes the head of the hierarchy to generate
        inherited_class (str): HTML class name to apply once to all levels of the list
        child_class (str): HTML class name to apply once per step in the list (so Item 1-1 would have it once,
                           Item 1-1-1 would have it twice, etc.).  Useful for incrementing tab behaviour
        depth (int): Maximum number of levels to recurse in the sidebar.  Default is all levels
        budget_collection: A budget collection that defines the full budget structure.  Used to get budget amount and
                           child categories
        show_categories (bool): If True, the list will show the categories from any bottom node Budgets as an extra
                                list item with className categories.

    Returns:
        (list): List of html elements for use as the children attribute of a html.Ul
    """
    this_className = f"{inherited_class} {child_class}"
    content = []

    for name in data[top_item]:
        if budget_collection:
            budget = budget_collection.get_budget_by_name(name)
            amount = budget.amount
            categories = budget.categories
        else:
            amount = ""
            categories = []

        content.append(html.Li(
            children=f"{name} ({amount})",
            id=generate_checklist_li_id(name),
            className=this_className,
        ))

        show_this_categories = False

        if depth > 0:
            if name in data:
                nested_children = make_sidebar_children(data,
                                                        name,
                                                        inherited_class=this_className,
                                                        child_class=child_class,
                                                        depth=depth-1,
                                                        budget_collection=budget_collection,
                                                        show_categories=show_categories
                                                        )
                content.append(html.Ul(
                    id=generate_checklist_ul_id(name),
                    children=nested_children,
                ))
            else:
                show_this_categories = True
        else:
            show_this_categories = True

        # If we are at full depth or there are no budgets below us, and this budget has more than one category, add an
        # unclickable Li with all the categories in this budget
        if show_categories and show_this_categories and len(budget.categories) > 1:
            content.append(html.Li(
                children=str(categories),
                id=name + "_categories",
                className=this_className + " categories"
            ))

    return content


def make_sidebar_ul(data, top_item, inherited_class="", child_class="", depth=np.inf, budget_collection=None,
                    show_categories=True):
    """
    Returns a sidebar defined using a html.Ul with nested Li and Ul elements

    Optionally can have class names applied recursively to each level of child within the list (eg: for formatting)

    Args:
        See make_sidebar_children

    Returns:
        (html.Ul)
    """
    children = make_sidebar_children(data=data,
                                     top_item=top_item,
                                     inherited_class=inherited_class + " sidebar-li",
                                     child_class=child_class,
                                     depth=depth,
                                     budget_collection=budget_collection,
                                     show_categories=show_categories,
                                     )

    ul = html.Ul(id="sidebar-ul",
                 children=children,
                 className="sidebar-ul"
                 )
    return ul


def register_sidebar_list_click(n_clicks, ul_children):
    """
    Updates a nested set of Ul and Li objects based on click events.

    Args:
        n_clicks: Unused (defines the trigger event)
        ul_children: The children attribute of a watched Ul that contains a nested list defined by Li and Ul objects,
                     where any Li that is paired with a commonly named Ul is is a heading and any Li without a Ul is a
                     "leaf" node that represents an item that can be checked/unchecked.  Clicking a leaf Li will toggle
                     it's checked status, whereas clicking a heading will toggle the checked status of all
                     leaves below it.

    Returns:
        (dict): A dict of the updated item that can be converted directly to Plotly JSON format.
    """
    # Skip callback if nothing has been triggered (callback fires at app start which will raise exceptions)
    if dash.callback_context.triggered:
        clicked_li_id = json.loads(dash.callback_context.triggered[0]['prop_id'].split('.')[0])
    else:
        raise dash.exceptions.PreventUpdate()

    # Use the ul_children object as the state for the list.  Work on it directly by grabbing references to its mutable
    # components and modifying to form the returned object.

    # Determine whether the clicked Li is a leaf node or a header node that has children by looking for a Ul with a
    # common id
    paired_ul_id = generate_checklist_ul_id(clicked_li_id['id'])
    paired_ul_path = get_path_to_id_in_serialized_ul(ul_children, paired_ul_id)

    # If found, get children under this.  Else, get the clicked li itself
    if paired_ul_path:
        leaves = get_leaves_below_sidebar_obj(ul_children, paired_ul_path)
    else:
        clicked_li_path = get_path_to_id_in_serialized_ul(ul_children, clicked_li_id)
        leaves = [get_by_path(ul_children, clicked_li_path)]

    # Determine whether to click or unclick all leaves
    # If all leaves are clicked, unclick them.  Otherwise, make them all clicked regardless of current status
    checked_status = get_leaves_checked_status(leaves)
    new_status = not all(checked_status)

    # Apply new status to leaves
    for leaf in leaves:
        leaf['props']['className'] = set_className_entry(leaf['props']['className'], "checked", new_status)

    return ul_children


def get_leaves_checked_status(leaves):
    checked_status = []
    for leaf in leaves:
        this_className = leaf['props']['className']
        checked_status.append(get_className_state(this_className, "checked"))
    return checked_status


def get_leaf_ids(leaves):
    return [leaf['props']['id']['id'] for leaf in leaves]


def get_checked_leaves(leaves):
    checked_status = get_leaves_checked_status(leaves)
    leaf_ids = get_leaf_ids(leaves)
    return [leaf_id for leaf_id, checked in zip(leaf_ids, checked_status) if checked]


def get_checked_sidebar_children(ul_children):
    """
    Returns the leaves of a sidebar that are checked as a list
    """
    leaves = get_leaves_below_sidebar_obj(ul_children, path_to_obj=tuple())
    checked_leaves = get_checked_leaves(leaves)
    return checked_leaves