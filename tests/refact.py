from physcraper import generate_ATT_from_phylesystem, generate_ATT_from_files, prune_short, config_obj, IdDicts,  PhyscraperScrape
import pickle
import sys
import os


study_id = "pg_873"
tree_id = "tree1679"
seqaln = "tests/data/minitest.fas"
mattype="fasta"
runname="fresh3"


configfi = "tests/local.config"

conf = config_obj(configfi)

data_obj = generate_ATT_from_phylesystem(seqaln,
                     mattype,
                     "tmp",
                     study_id = study_id,
                     tree_id = tree_id,
                     phylesystem_loc = 'local')


prune_short(data_obj)
data_obj.write_files()
data_obj.write_labelled()


ids = IdDicts(conf.ott_ncbi, "tmp")

scraper =  PhyscraperScrape(data_obj, ids, conf)
scraper.run_blast()
scraper.read_blast()


#otu_json = "tests/minitest_otu.json"
#treefile = "tests/minitest.tre"
#info_obj2 = StudyInfo(seqaln,
#                     mattype,
                      #"tmp"
#                     otu_json = otu_json,
#                     treefile = treefile)

#data_obj2 = info_obj.generate_ATT()

info_obj2 = generate_ATT_from_files("tmp/physcraper.fas",
                                   mattype,
                                   "tmp",
                                   "tmp/physcraper.tre",
                                    "tmp/otus.json",
                                   ingroup_mrca=data_obj.ott_mrca)