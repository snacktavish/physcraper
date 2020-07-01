How to run Physcraper using `physcraper_run.py`


## Simple Run

For the simplest `physcraper` run you just need the study id and tree id from OpenTree (see how to get those in FindTrees.md),
and an alignment file that goes with that tree.

    physcraper_run.py -s <study_id> -t <tree_id> -a <alignment_file_path> -as <alignment_schema> -o <output_directory>


To update this tree
https://tree.opentreeoflife.org/curator/study/view/ot_350/?tab=home&tree=Tr53296

(alignment already downloaded from treebase)


    physcraper_run.py -s ot_350 -t Tr53297 -a docs/examples/ot_350Tr53297.aln -as nexus -o ot_350_analysis


## Configuration paramaters


To see all the config paramaters, use `physcraper_run.py -h`


### Input Data


Tree information (required)
  -s STUDY_ID, --study_id STUDY_ID
                        OpenTree study id
  -t TREE_ID, --tree_id TREE_ID
                        OpenTree tree id

OR 

  -tf TREE_FILE, --tree_file TREE_FILE
                        a path to a tree file
  -tfs TREE_SCHEMA, --tree_schema TREE_SCHEMA
                        tree file format schema
  -ti TAXON_INFO, --taxon_info TAXON_INFO
                        taxon info file from OpenTree TNRS 



Alignment information (required)

  -a ALIGNMENT, --alignment ALIGNMENT
                        path to alignment
  -as ALN_SCHEMA, --aln_schema ALN_SCHEMA
                        alignment schema (nexus or fasta)

OR

  -tb, --treebase       download alignment from treebase

Tree and alignment information are required.
After an analysis has been run, they can be reloaded from a directory from a previous run.

  -re RELOAD_FILES, --reload_files RELOAD_FILES
                        reload files and configureation from dir


REQUIRED:

  -o OUTPUT, --output OUTPUT
                        path to output directory

Optional:

  -st SEARCH_TAXON, --search_taxon SEARCH_TAXON
                        taxonomic id to constrain blast search. format ott:123
                        or ncbi:123. Deafult will use ingroup of tree on
                        OpenTree, or MRCA of input tip





### Configuration paramaters

The configuration paramaters may be set in a config file, and then passed into the analysis run. See example.config for an example.


  -c CONFIGFILE, --configfile CONFIGFILE
                        path to config file

If a config file input is combined with comand line configuration parameters, the command line values will ovverride those in the config file.


## Blast search paramaters

  -e EMAIL, --email EMAIL
                        email address for ncbi blast searches

  -r, --repeat          repeat search until no no sequences are found


  -ev EVAL, --eval EVAL
                        blast evalue cutoff
  -hl HITLIST_LEN, --hitlist_len HITLIST_LEN
                        number of blast searches to save per taxon


You can use a local blast database:
To setup see doc/LocalDB.md

  -db BLAST_DB, --blast_db BLAST_DB
                        local download of blast database




  -nt NUM_THREADS, --num_threads NUM_THREADS
                        number of threads to use in processing


You can use your own blast database, for example set up on an AWS server.

\
## Sequence filtering parameters

  -tp TRIM_PERC, --trim_perc TRIM_PERC
                        minimum percentage of seqs end of alignemnts
  -rl RELATIVE_LENGTH, --relative_length RELATIVE_LENGTH
                        max relative length of added seqs, compared to input
                        aln len
  -spn SPECIES_NUMBER, --species_number SPECIES_NUMBER
                        max number of seqs to include per species

  -de DELAY, --delay DELAY
                        how long to wait before blasting the same sequence
                        again

#### Tree search parameters
  -no_est, --no_estimate_tree
                        don't estimate tree (default is False)

  -bs BOOTSTRAP_REPS, --bootstrap_reps BOOTSTRAP_REPS
                        number of bootstrap reps


#### Internal arguments


  -tx TAXONOMY, --taxonomy TAXONOMY
                        path to taxonomy


Example commands:



The simplest (but slowest) run is to choose a tree from opentree, and `physcraper` gets the alignment for you from treebase (argument `-tb`), using web blast:  

    physcraper_run.py -s pg_55 -t tree5864 -tb -o pg55_treebase 


The fastest way is to choose a tree from opentree, give the path to the corresponding downloaded alignment (argument `-a`) and a local blast directory (argument `-db`). To set up the local blast DB see [Local DB](setting_up_local_database):  

    physcraper_run.py -s ot_350 -t Tr53297 -a docs/examples/ot_350Tr53297.aln -as "nexus" -db ~/ncbi/localblastdb/ -o ot_350


To check tree download and the matching of names across tree and alignment without running the blast and tree estimation steps, use the flag (-no_est):  
  
    physcraper_run.py -s pg_55-t tree5864 --treebase -db ~/ncbi/localblastdb/ -no_est -o pg55_C

  Take a look at the tree, the alignemnt and the out_info csv file. It will list all taxa by their unique identifiers.


To then run a blast search and estimate an updated tree from that tree and alignemnt, you can re-load from that directory. It will use your same config settings (which weere automatically written out to outputdir/run.config).

If the run completed, re-run will use the final output ree and alignment. If the run was not compelte, it will reload the input files.


    physcraper_run.py -re pg_55_C -o pg_55_C


To re-run with a different configuration file, 

    physcraper_run.py -re  pg_55_C/ -c alt_config -o  pg_55_D


Configuration parameters can be either set in a cofniguration file using -c (e.g. data.config)

    physcraper_run.py -s ot_350 -t Tr53297 -a ot_350Tr53297.aln -nt 8 -spn 3 -hl 20 -as "nexus" -c data.config -o output4


Or they can be modified in the command line arguments. If you combine a configuration file with command line configuration paratemeters, the command line arguments will be used.

    physcraper_run.py -s pg_55 -t tree5864 -a treebase_alns/pg_55tree5864_ndhf.aln -nt 8 -spn 3 -hl 20 -as "nexus" -db ~/ncbi/localblastdb/ -o output4


To run on local files, not on trees in Open Tree, you need to match the labels to taxa using https://tree.opentreeoflife.org/curator/tnrs/  

    physcraper_run.py -tf tests/data/tiny_test_example/test.tre -tfs newick -a tests/data/tiny_test_example/test.fas --taxon_info tests/data/tiny_test_example/main.json -as fasta -o owndata


The current configuration settings are written to standard out, and saved in the output directory as run.config
e.g. 

    [blast]
    Entrez.email = None
    e_value_thresh = 1e-05
    hitlist_size = 20
    location = local
    localblastdb = /home/ejmctavish/ncbi/localblastdb/
    url_base = None
    num_threads = 8
    delay = 90
    [physcraper]
    spp_threshold = 3
    seq_len_perc = 0.8
    trim_perc = 0.8
    min_len = 0.8
    max_len = 1.2
    taxonomy_path = /home/ejmctavish/projects/otapi/physcraper/taxonomy



