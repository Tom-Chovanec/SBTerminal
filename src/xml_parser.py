import xml.etree.ElementTree as ET
import xml.dom.minidom

class XMLParser:
    @staticmethod
    def parse(xml_string: str) -> dict:
        try:
            root = ET.fromstring(xml_string)
            return XMLParser._element_to_dict(root)
        except ET.ParseError as e:
            print(f"ERROR: Failed to parse XML - {e}")
            return {}

    @staticmethod
    def _element_to_dict(element: ET.Element) -> dict:
        parsed_data = {element.tag: {} if list(element) else element.text.strip(
        ) if element.text and element.text.strip() else ""}
        for child in element:
            if isinstance(parsed_data[element.tag], dict):
                parsed_data[element.tag].update(
                    XMLParser._element_to_dict(child))
            else:
                parsed_data[element.tag] = XMLParser._element_to_dict(child)
        return parsed_data
    
    @staticmethod
    def get_value(xml_dict: dict, key: str, default=None):
        """Recursively search for a key in a nested dictionary."""
        if key in xml_dict:
            return xml_dict[key]

        for value in xml_dict.values():
            if isinstance(value, dict):
                found = XMLParser.get_value(value, key, default)
                if found is not None:
                    return found

        return default

    @staticmethod
    def dict_to_xml(data: dict) -> str:
        def build_xml(element_name, value):
            element = ET.Element(element_name)
            if isinstance(value, dict):
                for k, v in value.items():
                    element.append(build_xml(k, v))
            else:
                element.text = str(value)
            return element

        if not isinstance(data, dict) or len(data) != 1:
            raise ValueError(
                "Input dictionary must have exactly one root element.")

        root_name, root_value = next(iter(data.items()))
        root_element = build_xml(root_name, root_value)

        raw_xml = ET.tostring(root_element, encoding="utf-8")
        parsed_xml = xml.dom.minidom.parseString(raw_xml)
        return parsed_xml.toprettyxml(indent="  ")
    
    



