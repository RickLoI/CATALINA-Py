"""XML helpers replicating the DOM calls used by the Java loaders.

Java ``element.getElementsByTagName(tag)`` returns every DESCENDANT with that tag, in document
order (never the element itself): ``descendants`` below. ``getTextContent()`` concatenates the
text of the whole subtree: ``text_content``. ``Get_Element_Text_Content`` returns the text of the
first descendant, or "" when absent.
"""
from __future__ import annotations

import os
import sys
import traceback
import xml.etree.ElementTree as ET
from typing import List, Optional


def get_document_xml(filename: Optional[str]) -> Optional[ET.Element]:
    """Java: TLong_Memory.Get_Document_Xml. Returns the root element or None (error is printed)."""
    if filename is None or filename == "":
        print("TLong_Memory - error in Filename: " + str(filename), end="")
        return None
    if not os.path.exists(filename):
        print(f"Error: The Filename '{filename}' doesn't exist!", file=sys.stderr)
        return None
    try:
        return ET.parse(filename).getroot()
    except (ET.ParseError, OSError, ValueError):
        traceback.print_exc()
        return None


def descendants(parent: ET.Element, tag: str) -> List[ET.Element]:
    return list(parent.iter(tag))[1:] if parent.tag == tag else list(parent.iter(tag))


def text_content(node: ET.Element) -> str:
    return "".join(node.itertext())


def get_element_text_content(parent: ET.Element, tag: str) -> str:
    nodes = descendants(parent, tag)
    if nodes:
        return text_content(nodes[0])
    return ""


def get_all_text_contents(parent: ET.Element, tag: str) -> List[str]:
    return [text_content(n) for n in descendants(parent, tag)]
