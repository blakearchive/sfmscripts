import blake_xml


def get_obj(xml_path, obj_number):
    bxml = blake_xml.BlakeXML(xml_path)
    obj = bxml.objects()[obj_number]
    return bxml, obj


def text_equality(corr_file, test_obj):
    corr = ''
    with open(corr_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            corr += line
    return corr == test_obj.text()

bxml, obj = get_obj('data/vda.h.xml', 4)


def test_path():
    assert bxml.path == 'data/vda.h.xml'


def test_xml_parse():
    assert type(bxml.xml) == blake_xml.etree._ElementTree


def test_objects():
    assert len(bxml.objects()) == 11


def test_text_equality_001():
    assert text_equality('data/vda.h.illbk.05.txt', obj)


# .text should provide text for any <l> node under <phystext>.
    # test that phystext/*/l text is included
def test_text_for_all_l_children_001():
    _, o = get_obj('data/vda.h.xml', 4)
    assert text_equality('data/vda.h.illbk.05.txt', o)


    # test that phystext/*/*/*/l text is included
def test_text_for_all_l_children_002():
    _, o = get_obj('data/ahania.a.xml', 4)
    assert text_equality('data/ahania.a.illbk.05.txt', o)


# Note text should not be rendered in the transcription.
# e.g. don't print:
#       <note>In Copy O, the etched number "7" in the upper right-hand corner
#             is obscured by washes.</note>
def test_note_stripping():
    _, o = get_obj('data/vda.o.xml', 9)
    assert 'In Copy O' not in o.text()


# "space" nodes need to be replaced with a space. So that the following, for
# example, will have proper spacing:
#       Jehovah<space extent="1"/>What Vengeance dost thou require
def test_spacing():
    _, o = get_obj('data/abel.a.xml', 0)
    assert 'JehovahWhat' not in o.text()


# Test fails
# Some xml files have '\u0097' characters that should be cleaned up in
# the xml. They were probably meant to be em dashes in windows-1252. If the
# characters are included in the SuperfastMatch input, it may or may not
# affect fragments/matching, but in any case, if the chars are to be removed
# it ought to be done in the xml files rather than the transformation code.
def test_control_chars():
    _, o = get_obj('data/abel.a.xml', 0)
    assert '\u0097' not in o.text()
