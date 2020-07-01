import sys
import os
import json
from physcraper import generate_ATT_from_files, AlignTreeTax, OtuJsonDict, ConfigObj, IdDicts
from pytest import mark
from physcraper.opentree_helpers import bulk_tnrs_load



web = mark.web


def test_owndata():
    seqaln= "tests/data/tiny_test_example/test.fas"
    mattype="fasta"
    trfn= "tests/data/tiny_test_example/test.tre"
    schema_trf = "newick"
    workdir="tests/output/owndata"
    configfi = "tests/data/test.config"
    id_to_spn = r"tests/data/tiny_test_example/test_nicespl.csv"
    otu_jsonfi = "{}/otu_dict.json".format(workdir)

    """Tests if your own input files will generate a data object of class AlignTreeTax
    """

    if not os.path.exists("{}".format(workdir)):
        os.makedirs("{}".format(workdir))

    ids = IdDicts()
    if os.path.exists(otu_jsonfi):
        print("load json")
        otu_json = json.load(open(otu_jsonfi))
    else:
        otu_json = OtuJsonDict(id_to_spn, ids)
        json.dump(otu_json, open(otu_jsonfi,"w"))

    data_obj = generate_ATT_from_files(alnfile=seqaln,
                                 aln_schema=mattype,
                                 workdir=workdir,
                                 configfile=configfi,
                                 treefile=trfn,
                                 tree_schema = schema_trf,
                                 otu_json=otu_jsonfi,
                                 search_taxon=None)


    assert isinstance(data_obj, AlignTreeTax)


import physcraper
from dendropy import DnaCharacterMatrix

@web
def test_opentree():
    # Use OpenTree phylesystem identifiers to get study and tree
    study_id = "pg_873"
    tree_id = "tree1679"
    seqaln = "tests/data/minitest.fas"
    mattype = "fasta"
    workdir = "tests/output/opentree"
    configfi = "tests/data/remotencbi.config"

    sys.stdout.write("\nTesting 'opentree scrape (1 round)'\n")
    conf = physcraper.ConfigObj(configfi, interactive=False)
    # print "1. {}".format(conf.email)
          
    aln = DnaCharacterMatrix.get(path=seqaln, schema=mattype)
    data_obj = physcraper.generate_ATT_from_phylesystem(alnfile=aln,
                                                        workdir=workdir,
                                                        configfile=conf,
                                                        study_id=study_id,
                                                        tree_id=tree_id)
    assert isinstance(data_obj, AlignTreeTax)

def load_json():
    inputfi = "tests/data/bulk_tnrs.json"
    otu_dict = bulk_tnrs_load(inputfi)
    assert len(otu_dict) == 16
    print(otu_dict)



def test_owndata_bulktnrs():
    seqaln= "tests/data/tiny_test_example/test.fas"
    mattype="fasta"
    trfn= "tests/data/tiny_test_example/test.tre"
    schema_trf = "newick"
    workdir="tests/output/owndata"
    configfi = "tests/data/test.config"
    otu_jsonfi = "tests/data/tiny_test_example/main.json"

    """Tests if your own input files will generate a data object of class AlignTreeTax
    """

    if not os.path.exists("{}".format(workdir)):
        os.makedirs("{}".format(workdir))

    conf = ConfigObj(configfi)

    otu_dict = bulk_tnrs_load(otu_jsonfi)  
    print(otu_dict)
    data_obj = generate_ATT_from_files(alnfile=seqaln,
                                 aln_schema=mattype,
                                 workdir=workdir,
                                 configfile=configfi,
                                 treefile=trfn,
                                 tree_schema = schema_trf,
                                 otu_json=otu_dict,
                                 search_taxon=None)


    assert isinstance(data_obj, AlignTreeTax)


test_owndata_bulktnrs()