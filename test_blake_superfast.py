import itertools
import simplejson as json
import pytest
import yaml
import blake_superfast as blake


#
# Specify SuperfastmatchAPI connection info in superfast.yaml
#

# region api

with open('superfast.yaml') as infile:
    cfg = yaml.safe_load(infile)
addr = cfg['addr']
port = cfg['port']

api = blake.API


def test_default_addr():
    assert api.addr == addr


def test_default_port():
    assert api.port == port


def test_base_url():
    assert api.base_url == f'http://{addr}:{port}/'

api2 = blake.SuperfastAPI('null.example.com', '1111')


def test_custom_addr():
    assert api2.addr == 'null.example.com'


def test_custom_port():
    assert api2.port == '1111'


def test_api_connection():
    assert api.get(['status'], yield_json=False)[0:14] == '{\n    "success'


def test_api_get():
    assert api.get(['document', '1'])['metaData']['fields'][4] == 'title'


def test_api_url():
    api.get(['status'], yield_json=False)
    assert api.url[-12:] == ':8080/status'

docs = [x for x in itertools.islice(api.documents(perpage='2'), 0, 3)]


def test_api_documents_paginate():
    assert len(docs) == 3


def test_api_documents_docs():
    assert type(docs[0]) == blake.BlakeDoc

# endregion

# region doc

doc001 = blake.BlakeDoc.from_json('data/vda.h.illbk.07.json')


def test_init_from_json_dict():
    with open('data/vda.h.illbk.07.json', 'r') as json_file:
        json002 = json.load(json_file)
    doc002 = blake.BlakeDoc.from_json(json002)
    assert doc001.title == doc002.title


def test_doctype():
    assert doc001.doctype == 1


def test_docid():
    assert doc001.docid == 89


def test_title():
    assert doc001.title == 'vda.h.illbk.07.txt'


def test_desc_id():
    assert doc001.desc_id == 'vda.h.illbk.07'


def test_work():
    assert doc001.work == 'vda'


def test_copy():
    assert doc001.copy == 'h'


def test_form():
    assert doc001.form == 'illbk'


def test_page():
    assert doc001.page == '07'


def test_short_title():
    short_doc = blake.BlakeDoc.from_json('data/but518.wc.01.txt')
    assert not (short_doc.work or short_doc.copy or short_doc.form or
                short_doc.page)


def test_text_001():
    assert doc001.text[0:10] == 'Wave shado'


def test_text_002():
    assert doc001.text[-9:] == 'e night,\n'


def test_fragment_head():
    assert doc001.fragment(0, 10) == 'Wave shado'


def test_fragment_tail():
    assert doc001.fragment(1488, 10) == 'e night,\n'


def test_matches_contains_all_matches():
    assert len(list(doc001.matches())) == 10


def test_matches_contains_SuperfastDocmatches():
    assert type(next(doc001.matches())) == blake.SuperfastDocmatch

# endregion

# region match
m001 = next(doc001.matches())


def test_match_primary_doc():
    assert m001.primary_doc.title == 'vda.h.illbk.07.txt'


def test_match_matching_doc():
    assert m001.matching_doc.title == 'vda.g.illbk.07.txt'


def test_match_fragments_generator():
    assert len(list(m001.fragments())) == 4

# excluded function tests under matrix-relations

# endregion

# region fragment

frag_list = [30, 28, 370, 4200547186]
frag_list_str = [30, '28', '370', 4200547186]
frag_001 = blake.MatchFragment(doc001, frag_list)
frag_001_str = blake.MatchFragment(doc001, frag_list)


def test_lst():
    assert frag_001.lst == frag_list


def test_begin():
    assert frag_001.begin == 28


def test_length():
    assert frag_001.length == 370


def test_begin_str():
    assert frag_001_str.begin == 28


def test_length_str():
    assert frag_001_str.length == 370


def test_frag_text_001():
    assert frag_001.text[:10] == 'and in wha'


def test_frag_text_002():
    assert frag_001.text[-10:] == 'into a pre'
# endregion

# region matrix-relations
matrix_csv_path = 'blake-relations.csv'
matrices = blake.MatrixRelations(matrix_csv_path)


# Objects with no other objects from the same matrix are not
# present in MatrixRelations.matrices
def test_docs_no_same_matrix():
    assert 'milton.d.illbk.05' not in matrices.matrices

slos_e = blake.BlakeDoc.from_json('data/s-los.e.illbk.06.json')
slos_c = blake.BlakeDoc.from_json('data/s-los.c.illbk.06.json')


def test_excluded():
    assert matrices.same_matrix(slos_e, slos_c)


def test_excluded_diff():
    assert not matrices.same_matrix(slos_e, doc001)


mx001 = blake.SuperfastDocmatch(slos_e, match_doc=slos_c)
mx002 = blake.SuperfastDocmatch(slos_e, match_doc=doc001)


def test_match_excluded_none():
    with pytest.raises(AttributeError):
        mx001.excluded()


def test_match_same_matric():
    blake.SuperfastDocmatch.exclusions = matrices.matrices
    assert mx001.excluded()


def test_match_excluded_diff():
    blake.SuperfastDocmatch.exclusions = matrices.matrices
    assert not mx002.excluded()
# endregion
