from lxml import etree
import json

path = r'Путь к XML файлу'
tree = etree.parse(path)
root = tree.getroot()

# Получаем только первые три definition
definitions = root.xpath('.//*[local-name() = "definitions"]/*')[:3]

def process_criteria(criteria_element):
    criteria_dict = {
        "operator": criteria_element.get('operator')
    }
    
    criterions = []
    for criterion in criteria_element.xpath('./*[local-name() = "criterion"]'):
        criterions.append({
            "comment": criterion.get('comment'),
            "test_ref": criterion.get('test_ref')
        })
    
    if criterions:
        criteria_dict["criterion"] = criterions
    
    inner_criteria_elements = []
    for inner_criteria in criteria_element.xpath('./*[local-name() = "criteria"]'):
        processed_inner_criteria = process_criteria(inner_criteria)
        if processed_inner_criteria.get("criterion") or processed_inner_criteria.get("criteria"):
            inner_criteria_elements.append(processed_inner_criteria)

    if inner_criteria_elements:
        criteria_dict["criteria"] = inner_criteria_elements
    
    return criteria_dict

output = {
    "definitions": [],
    "tests": [],
    "objects": [],
    "states": [],
    "variables": []
}

test_ids = set()
object_refs = set()
state_refs = set()
variable_ids = set()

for definition in definitions:
    def_dict = {
        "class": definition.get('class'),
        "id": definition.get('id'),
        "version": definition.get('version'),
        "metadata": {
            "affected": {},
            "references": []
        }
    }
    metadata_obj = definition.getchildren()[0]
    for metadata_child in metadata_obj.getchildren():
        metadata_child_tag = metadata_child.tag
        if metadata_child_tag.endswith('title'):
            def_dict["metadata"]["title"] = metadata_child.text
        elif metadata_child_tag.endswith('reference'):
            def_dict["metadata"]["references"].append(dict(metadata_child.attrib))
        elif metadata_child_tag.endswith('affected'):
            def_dict["metadata"]["affected"]["family"] = metadata_child.get("family")
            platform = metadata_child.getchildren()[0]
            def_dict["metadata"]["affected"]["platform"] = platform.text
    criteria_tests = definition.xpath('.//*[local-name() = "criterion"]/@test_ref')
    test_ids.update(criteria_tests)


    criteria_elements = definition.xpath('.//*[local-name() = "criteria"]')
    if criteria_elements:
        criteria_result = process_criteria(criteria_elements[0])
        if criteria_result:
            def_dict["criteria"] = criteria_result
    
    output["definitions"].append(def_dict)

tests = root.xpath('.//*[local-name() = "tests"]/*')
for test in tests:
    test_id = test.get('id')
    if test_id in test_ids:
        test_dict = {
            "check": test.get('check'),
            "comment": test.get('comment'),
            "id": test_id,
            "version": test.get('version'),
            "test_body": []
        }
        test_children = test.getchildren()
        object_ref = test_children[0]
        state_ref = test_children[1]

        object_ref_attrib = object_ref.attrib['object_ref']
        state_ref_attrib = state_ref.attrib['state_ref']
        test_dict["test_body"].append({'object_ref':object_ref_attrib})
        test_dict["test_body"].append({'state_ref':state_ref_attrib})
        
        object_refs.add(object_ref_attrib)
        state_refs.add(state_ref_attrib)

        output["tests"].append(test_dict)

objects = root.xpath('.//*[local-name() = "objects"]/*')
for object in objects:
    object_id = object.get('id')
    if object_id in object_refs:
        object_dict = {
            "id": object_id,
            "version": object.get('version'),
            "object_childrens" : []
        }

        object_childrens = object.getchildren()
        for object_child in object_childrens:
            object_child_dict = {}
            tag = object_child.tag.split('}')[1]
            object_child_dict["tag"] = tag
            child_text = object_child.text
            if child_text:
                object_child_dict["text"] = child_text
            child_attrib = object_child.attrib
            if child_attrib:
                object_child_dict['attributes']= [dict(child_attrib)]
            object_dict["object_childrens"].append(object_child_dict)            

        output["objects"].append(object_dict)

states = root.xpath('.//*[local-name() = "states"]/*')
for state in states:
    state_id = state.get("id")
    if state_id in state_refs:
        state_dict = {
            "id": state_id,
            "version": state.get('version'),
            "state_children": []
        }
        state_children = state.getchildren()
        for state_child in state_children:
            state_child_dict = {}
            state_parameter = state_child.text
            state_attribs = state_child.attrib
            if "var_ref" in state_attribs.keys():
                variable_ids.add(state_attribs.get("var_ref"))
            state_child_dict["parameter"] = state_parameter
            state_child_dict["expression"] = dict(state_attribs)
            state_dict["state_children"].append(state_child_dict)
        output["states"].append(state_dict)

variables = root.xpath('.//*[local-name() = "variables"]/*')
for variable in variables:
    variable_id = variable.get("id")
    if variable_id in variable_ids:
        variable_dict = {
            "id": variable_id,
            "version": variable.get('version'),
            "datatype": variable.get('datatype'),
            "comment": variable.get('comment'),
            "arithmetic" : {
                "arithmetic_body": []
            }
        }
        arithmetic = variable.getchildren()[0]
        variable_dict["arithmetic"]["arithmetic_operation"] = arithmetic.get("arithmetic_operation")
        for arithmetic_children in arithmetic.getchildren():
            arithmetic_children_dict = {}
            tag = arithmetic_children.tag.split("}")[1]
            text = arithmetic_children.text
            attribs = dict(arithmetic_children.attrib)
            arithmetic_children_dict["tag"] = tag
            arithmetic_children_dict["attributes"] = attribs
            if text:
                arithmetic_children_dict["data"] = text
            variable_dict["arithmetic"]["arithmetic_body"].append(arithmetic_children_dict)
        output["variables"].append(variable_dict)

json_output = json.dumps(output, indent=4, ensure_ascii=False)
with open('output.json', 'w', encoding='utf-8') as f:
    f.write(json_output)