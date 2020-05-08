import os 


#expected_keys = ['seq_len_perc', 'num_threads', 'phylesystem_loc', 'ncbi_parser_names_fn', 'ncbi_parser_nodes_fn', 'gb_id_filename', 'unmapped', 'hitlist_size', 'id_pickle', 'blast_loc', 'url_base', 'ott_ncbi', 'email', 'e_value_thresh', 'blastdb']
# expected_keys = ['email', 'e_value_thresh', 'hitlist_size', 'blast_loc', 'blastdb', 'url_base',  'ncbi_parser_nodes_fn', 'ncbi_parser_names_fn', 'num_threads', 'gb_id_filename', 'delay',  'unmapped', 'seq_len_perc', 'seq_len_perc', 'trim_perc', 'phylesystem_loc', 'ott_ncbi', 'id_pickle' ]



def test_config():
    from physcraper import ConfigObj
    configfi = "tests/data/test.config"
    workdir = "tests/tmp"
    if not os.path.exists(workdir):
        os.makedirs(workdir)
    conf = ConfigObj(configfi, interactive=False)
    print(conf.__dict__.keys())

    if conf.blast_loc == "local":
        expected_keys = [ 'seq_len_perc', 'num_threads', 'maxlen', 'hitlist_size', 'delay', 'taxonomy_dir', 'trim_perc', 'url_base', 'ott_ncbi', 'blast_loc','email', 'e_value_thresh', 'blastdb']
    else:
        expected_keys = ['seq_len_perc', 'num_threads', 'maxlen', 'hitlist_size', 'delay', 'trim_perc', 'url_base', 'ott_ncbi', 'blast_loc', 'taxonomy_dir', 'email', 'e_value_thresh']

    assert len(conf.email.split("@")) == 2
    #    assert conf.url_base == None
    assert set(expected_keys).issubset(set(conf.__dict__.keys()))
    conf.write_file(workdir)

    defaultconf = ConfigObj()
    reconf = ConfigObj("{}/run.config".format(workdir))

test_config()