## An overview of the Physcraper results files

### - Input files

Physcraper rewrites input files for a couple reasons: reproducibility, taxon name matching, and taxon reconciliation.
It writes the config file down if none was provided. Everything is written into the inputs_TAG folder.

### - Run files

All run files are also automatically written down by Physcraper in the run_TAG folder: Blast runs, alignments, raxml trees, bootstrap, etc.

The trees are reconstructed using RAxML, with tip labels corresponding to local ids (e.g., otu42009, otuPS1) and not taxon names (e.g., *Ceiba*), nor taxonomic ids (e.g., ott or ncbi). Branch lengths are proportional to relative substitution rates.

### - Output files

An updated tree in nexson format, containing all types of tip labels is saved in here.
From this tree, a tree with any kind of label can be produced.
By default, the updtaed tree with taxon names as tip labels is saved
in the `output_tag` folder as `updated_taxonname.tre`. See section [relabeling the trees](# Relabeling) below for more info on how to generate trees with different types of labels.
