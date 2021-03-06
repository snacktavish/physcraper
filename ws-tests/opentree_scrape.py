import sys
import physcraper
from physcraper.opentree_helpers import scraper_from_opentree


# Use OpenTree phylesystem identifiers to get study and tree
configfi = "docs/examples/example.config"
study_id = "ot_350"
tree_id = "Tr53297"
workdir ="scrape_ot_350_compact"

aln_fi = "docs/examples/{}{}.aln".format(study_id, tree_id)


# Create an 'scraper' object to get data from NCBI, align it an
scraper = scraper_from_opentree(study_id = study_id, 
                                tree_id = tree_id, 
                                alnfile = aln_fi, 
                                aln_schema = "nexus", 
                                configfile = configfi, 
                                workdir = workdir)

sys.stdout.write("{} taxa in alignement and tree\n".format(len(scraper.data.aln)))


#scraper.read_blast_wrapper()
scraper.est_full_tree()
scraper.data.write_labelled(label='^ot:ottTaxonName')