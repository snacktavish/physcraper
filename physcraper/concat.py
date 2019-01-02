#!/usr/bin/env python
# coding=utf-8
from __future__ import unicode_literals


import os
import sys
import subprocess
import csv
import pickle
import random
import physcraper

from copy import deepcopy
from dendropy import Tree, DnaCharacterMatrix



# if sys.version_info < (3, ):
#     from urllib2 import HTTPError
# else:
#     from urllib.error import HTTPError

"""Code used to concatenate different single PhyScraper runs into a concatenated one.
"""

print("Current concat version number: 01-02-2019.0")


def remove_aln_tre_leaf(scrape):
    """Attempt to remove all occurrences in aln and tre of otu,
     that were removed sometime in the single runs, but kind of sneak in.
    """
    aln_ids = set()
    for tax in scrape.aln:
        aln_ids.add(tax.label)
    assert aln_ids.issubset(scrape.otu_dict.keys())

    treed_taxa = set()
    for leaf in scrape.tre.leaf_nodes():
        treed_taxa.add(leaf.taxon)
    for leaf in scrape.tre.leaf_nodes():
        if leaf.taxon not in aln_ids:
            scrape.tre.prune_taxa([leaf])
            scrape.tre.prune_taxa_with_labels([leaf.taxon])
            scrape.tre.prune_taxa_with_labels([leaf])
            treed_taxa.remove(leaf.taxon)
    assert treed_taxa.issubset(aln_ids)
    return scrape

# # seems not to be used anymore
# def add_to_del_acc(del_acc, gene, spn, random_gen):
#     """
#     Adds gb id to del_acc dictionary, which is used to remove gb_ids from tmp_dict so that they will
#     not be added to the concat dict twice.
# 
#     :param del_acc: dict with gb id that were added to concat_dict
#     :param gene: single-gene name, from where gb_id is from
#     :param spn: taxon name of gb_id
#     :param random_gen: ??
#     :return: updated del_acc
#     """
#     physcraper.debug(spn)
#     spn_ = spn.replace(" ", "_")
#     if gene in del_acc.keys():
#         if spn_ not in del_acc[gene].keys():
#             del_acc[gene][spn] = random_gen
#         else:
#             del_acc[gene][spn_.format("_", " ")] = random_gen
#     else:
#         del_acc[gene] = {spn: random_gen}
#     return del_acc


class Concat(object):
    """Combines several physcraper runs into a concatenated alignment and calculates a phylogeny.
    There are two options available, either data will be concatenated by random (per taxon name) or the 
    user provides a file which say, which sequences shall be concatenated.

    User need to make sure, that there are at least some overlapping lineages.
    Do not concatenate data from the same loci (if you want to expand an alignment, run physcraper!).

    To build the class the following is needed:
        workdir_comb: the path to your directory where the data shall be stored
        email: your email address, currently used to retrieve missing taxon information

    During the initializing process the following self objects are generated:
        self.workdir: the path to your directory
        self.sp_acc_comb: dictionary - similar to otu_dcit of Physcraper class
            key: taxon name
            value: dictionary:
                key: gene name
                value: dictionary:
                    key: unique identifier of concat_class
                    value: dictionary - key-value-pairs:
                        "unique_id": unique id - either user name or genbank accession number
                        "seq": corresponding sequence
                        "sp_id": taxon id
                        "original_PS_id": otu_id from single-gene run
                        "concat:status": "single run"/ "concatenated"
                        "new tipname": taxon name plus number if there are more than a single
                                        concatenated sequence per taxon
        self.single_runs: dictionary
            key: gene name, as provided by user in input
            value: file containing the single gene Physcraper run, loaded from pickle
        self.sp_counter: dictionary
            key: taxon name
            value: dictionary
                key: gene name
                value: number of sequences present for the given gene and taxon
        self.email: email
        self.comb_seq: dictionary
            key: gene name
            value: dictionary:
                key: taxon name
                value: sequence
        self.comb_acc: dictionary # !!! Note can be easily combined with comb_seq
            key: gene name
            value: dictionary:
                key: taxon name
                value: unique identifier of concat_class
        self.aln_all: dictionary
            key: numbers from 1 to amount of loci concatenated
            value: dendropy aln including empty seq
        self.num_of_genes = number corresponding to the number of genes that shall be concatenated
        self.genes_present = list of the gene names that shall be concatenated
        self.tre_as_start = phylogeny used as starting tree for concatenated run, is the one with most tips present
        self.tre_start_gene = corresponding name to tre_as_start
        self.short_concat_seq = list of taxa that have only few sequences information/short genes
        self.concat_tips: dictionary
            key: otu.label from self.tre_as_start.taxon_namespace
            value: taxon name
        self.concatfile = path to file if user supplied concatenation file is used
        self.concatenated_aln = concatenated alignment
        self.tmp_dict = subset of self.sp_acc_comb
        self.part_len = holds sequence partition position to write the partitioning file
        self.backbone = T/F, if you want to keep one of the phylogenies as constraint backbone
    """

    def __init__(self, workdir_comb, email):
        self.workdir = workdir_comb
        self.sp_acc_comb = {}
        self.single_runs = {}
        self.sp_counter = {}
        if not os.path.exists(self.workdir):
            os.makedirs(self.workdir)
        self.email = email
        self.comb_seq = {}
        self.comb_acc = {}
        self.aln_all = {}
        self.num_of_genes = 0
        self.genes_present = []
        self.tre_as_start = None
        self.tre_start_gene = None
        self.short_concat_seq = None
        self.concatfile = None
        self.part_len = None  # ! TODO MK: might not need to be self
        self.concatenated_aln = None
        self.tmp_dict = None
        self.concat_tips = {}
        self.backbone = False
        self.seq_filter = ['deleted', 'subsequence,', 'not', "removed", "deleted,",
                           "local"]  # TODO: Copy from physcraper class settings, try to import and read in here

    def load_single_genes(self, workdir, pickle_fn, genename):
        """Load PhyScraper class objects and make a single dict per run.

        Removes abandoned nodes first.

        :param workdir: directory of single gene run
        :param pickle_fn: path to pickled file of the Physcraper run
        :param genename: string, name for locus provided by user
        :return: self.single_runs
        """
        physcraper.debug("load_single_genes: {}".format(genename))
        scrape = pickle.load(open("{}/{}".format(workdir, pickle_fn), "rb"))
        scrape = remove_aln_tre_leaf(scrape)
        self.single_runs[genename] = deepcopy(scrape)
        return

    def combine(self):
        """Combines several PhyScraper objects to make a concatenated run dict.

        Is a wrapper function around make_concat_id_dict(). It produces the parameters needed for the function.
        """
        physcraper.debug("combine")
        self.num_of_genes = len(self.single_runs)
        concat_id_counter = 1
        for genename in self.single_runs:
            self.genes_present.append(genename)
            for otu in self.single_runs[genename].aln.taxon_namespace:
                concat_id = "concat_{}".format(concat_id_counter)
                self.make_concat_id_dict(otu.label, genename, concat_id)
                concat_id_counter += 1
        self.dump("load_single_data.p")
        return

    def make_concat_id_dict(self, otu, genename, concat_id):
        """Makes a concat_id entry with all information

        Note: has test

        :param otu: otu_id
        :param genename: name of single gene locus
        :param concat_id: unique identifier in the concat class
        :return: modified self.sp_acc_comb
        """
        data = self.single_runs[genename].otu_dict[otu]
        seq = str(self.single_runs[genename].aln[otu])
        tax_id = None
        # only add the information of sequences that were added
        if data['^physcraper:status'].split(' ')[0] not in self.seq_filter:
            if '^ncbi:taxon' in data:
                tax_id = "taxid_{}".format(data['^ncbi:taxon'])
            if tax_id is None or tax_id == "taxid_None":
                print("think about it")
                tn = data['^user:TaxonName'].replace("_", "").replace(" ", "")
                # print(tn)
                tax_id = "taxid_{}".format(tn).encode("ascii")
                # print(tax_id)
            assert tax_id.split("_")[1] is not None
            assert tax_id.split("_")[1] != "None"
            assert tax_id.split("_")[1] != ""
            if tax_id not in self.sp_acc_comb:
                self.sp_acc_comb[tax_id] = {}
            if genename not in self.sp_acc_comb[tax_id]:
                self.sp_acc_comb[tax_id][genename] = {}

            if concat_id not in self.sp_acc_comb[tax_id][genename]:
                unique_id = None
                if "^ncbi:accession" in data:
                    unique_id = data["^ncbi:accession"]
                elif u"^ot:originalLabel" in data:
                    unique_id = data[u"^ot:originalLabel"]
                assert unique_id is not None
                concat_dict = {
                    "unique_id": unique_id,
                    "seq": seq,
                    "sp_id": tax_id,
                    "original_PS_id": otu,
                    "concat:status": "single run",
                }
                self.sp_acc_comb[tax_id][genename][concat_id] = concat_dict
            else:
                physcraper.debug(
                    "something goes wrong, you should not try to add the same id several times...."
                )
            if concat_dict["sp_id"] is "taxid_None":
                # we should never get here....
                sys.stderr.write(
                    "There is no species name for the seq. Do not know how to concatenate then. "
                    "Please remove seq from aln: {}.".format(data["^ncbi:accession"])
                )
                physcraper.debug("THERE IS A SERIOUS PROBLEM....spn is none")
                if u'original_PS_id' in data:
                    tax_id = "taxid_{}".format(data[u'original_PS_id'])
                else:
                    tax_id = "taxid_{}".format(data['^ncbi:taxon'].format("_", ""))

                self.sp_acc_comb[tax_id] = self.sp_acc_comb[unique_id]
                del self.sp_acc_comb[unique_id]
        else:
            del self.single_runs[genename].otu_dict[otu]

    # # Seems not to be used
    # def get_taxon_info(self, key, data):
    #     """If there are no taxon information (for what ever reason) try again to obtain sp names.
    #
    #     If the key is not part of data, it will get the name through a web query using the GI number.
    #
    #     :param key: key of otu_dict/data that shall contain the taxon name, e.g.^ot:ottTaxonName
    #     :param data: otu_dict entry from single gene physcraper run
    #     :return: taxon name
    #     """
    #     # physcraper.debug("get_rank_info")
    #     tax_name = None
    #     if key in data:
    #         if data[key] is None:
    #             if "^ncbi:accession" in data:
    #                 gb_id = data["^ncbi:accession"]
    #                 Entrez.email = self.email
    #                 tries = 5
    #                 for i in range(tries):
    #                     try:
    #                         handle = Entrez.efetch(db="nucleotide", id=gb_id, retmode="xml")
    #                     except (IndexError, HTTPError) as err:
    #                         sys.stderr.write(err)
    #                         if i < tries - 1:  # i is zero indexed
    #                             continue
    #                         else:
    #                             raise
    #                     break
    #                 read_handle = Entrez.read(handle)[0]
    #                 tax_name = read_handle['GBSeq_feature-table'][0]['GBFeature_quals'][0]['GBQualifier_value']
    #         else:
    #             tax_name = data[key]
    #     assert tax_name is not None
    #     tax_name = tax_name.replace("_", " ")
    #     tax_name = tax_name.replace(".", "").replace("'", "")
    #     tax_name = tax_name.encode("ascii")
    #     return tax_name

    def sp_seq_counter(self):
        """Counts how many seq per sp and genes there are -is used by sp_to_keep.

        Note: has test

        :return: builds self.sp_counter
        """
        physcraper.debug("sp_seq_counter")
        for tax_id in self.sp_acc_comb:
            # print(spn)
            assert tax_id is not None, "tax_id `%s` is not known" % tax_id
            tmp_gene = deepcopy(self.genes_present)
            for gene in self.sp_acc_comb[tax_id]:
                tmp_gene.remove(gene)
                tax_new = tax_id   # .replace(" ", "_")
                if tax_new in self.sp_counter:
                    self.sp_counter[tax_new][gene] = len(self.sp_acc_comb[tax_id][gene])
                else:
                    self.sp_counter[tax_new] = {gene: len(self.sp_acc_comb[tax_id][gene])}
            for item in tmp_gene:
                if tax_new in self.sp_counter:
                    self.sp_counter[tax_new][item] = 0
                else:
                    self.sp_counter[tax_new] = {item: 0}
        physcraper.debug(self.sp_counter)

    def get_largest_tre(self):
        """Find the single gene tree with the most tips, which will be used as
        starting tree for concat phylo reconstruction.

        :return: fills in selfs to know which data is used as starting tree
        """
        physcraper.debug("get_largest_tre")
        first = True
        len_all_taxa = {}
        for gene in self.single_runs:
            len_aln_taxa = len(self.single_runs[gene].aln.taxon_namespace)
            len_all_taxa[gene] = len_aln_taxa
        len_max = 0
        gene_max = 0
        for gene, len_item in len_all_taxa.items():
            if first:
                len_max = len_item
                gene_max = gene
                assert len_max != 0
                assert gene_max != 0
                first = False
            if len_item > len_max:
                len_max = len_item
                gene_max = gene
        self.tre_as_start = self.single_runs[gene_max].tre
        self.tre_start_gene = gene_max

    def make_sp_gene_dict(self):
        """Is the build around to make the dicts that are used to make it into a concatenated
        dendropy :class:`DnaCharacterMatrix <dendropy.datamodel.charmatrixmodel.DnaCharacterMatrix>` alignment object
        """
        count = 2
        physcraper.debug("make_sp_gene_dict")
        if self.concatfile is not None:
            self.user_defined_concat()
        else:
            sp_to_keep = self.sp_to_keep()
            self.tmp_dict = deepcopy(self.sp_acc_comb)
            while len(self.tmp_dict.keys()) >= 1:
                del_acc = {}
                for tax_id in self.tmp_dict.keys():
                    sp_to_keep_list = sp_to_keep.keys()
                    if tax_id in sp_to_keep_list:
                        tmp_gene = deepcopy(self.genes_present)
                        # physcraper.debug("tmpdict")
                        # physcraper.debug(self.tmp_dict[tax_id])
                        for gene in self.tmp_dict[tax_id]:
                            tax_id_otu = []
                            for otu in self.single_runs[gene].otu_dict:
                                # physcraper.debug(otu)
                                tax = self.single_runs[gene].otu_dict[otu]['^ncbi:taxon']
                                if tax is None:
                                    tax = self.single_runs[gene].otu_dict[otu]['^user:TaxonName']
                                    # physcraper.debug(tax)
                                    tax = tax.replace("_", "").replace(" ", "")
                                    # physcraper.debug(tax)
                                tax_id_otu.append(str(tax))
                            assert tax_id.split("_")[1] in tax_id_otu  # , (tax_id.split("_")[1], tax_id_otu)
                            tmp_gene.remove(gene)
                            del_acc = self.select_rnd_seq(tax_id, gene, del_acc)
                        # physcraper.debug("tmp_gene")
                        # physcraper.debug(tmp_gene)

                        # produces empty sequence when name of gene was not removed in first step
                        for item in tmp_gene:
                            # add a 2 to the name when it occurs more often
                            # physcraper.debug(item)
                            # physcraper.debug(tax_id)
                            # physcraper.debug( self.comb_seq[item].keys())
                            # if str(tax_id) in self.comb_seq[gene].keys():
                            #     tax_id_new = "{}_{}".format(tax_id, count)
                            #     while tax_id_new in self.comb_seq[gene].keys():
                            #         count += 1
                            #         tax_id_new = "{}_{}".format(tax_id_, count)
                            #     tax_id = str(tax_id_new)
                            # physcraper.debug(tax_id)
                            self.make_empty_seq(tax_id, item)
                        self.rm_rnd_sp(del_acc)
                        tax_id = "{}_{}".format(str(tax_id).split("_")[0], str(tax_id).split("_")[1])
                        # physcraper.debug(tax_id)
                        # physcraper.debug(self.tmp_dict.keys())
                        del self.tmp_dict[tax_id]
                    else:
                        physcraper.debug("selse")
                        for gene in self.tmp_dict[tax_id]:
                            del_acc = self.select_rnd_seq(tax_id, gene, del_acc)
                        self.rm_rnd_sp(del_acc)
                    self.rm_empty_spn_entries(del_acc)
        # make sure all are of same length
        physcraper.debug("end of sp gene dict")
        len_gene = []
        for gen in self.comb_seq.keys():
            gene_taxid = (self.comb_seq[gen].keys())
            len_gene.append(gene_taxid)
        physcraper.debug(len(len_gene))
        physcraper.debug(range(0, (len(len_gene) - 1)))
        for item in range(0, (len(len_gene) - 1)):
            assert len_gene[item] == len_gene[item + 1]
        self.rename_drop_tips()

    def rename_drop_tips(self):
        """ Removes tips from tre as start that are not present in the concatenated aln
        and renames tips that are present.
        """
        physcraper.debug("rename_drop_tips")
        # leaf.taxon is never in concat_tips
        concat_tax = set()
        for leaf in self.tre_as_start.leaf_nodes():
            if leaf.taxon.label not in self.concat_tips.keys():
                self.tre_as_start.prune_taxa([leaf])
                self.tre_as_start.prune_taxa_with_labels([leaf.label])
                self.tre_as_start.prune_taxa_with_labels([leaf])
                self.tre_as_start.prune_taxa_with_labels([leaf.taxon.label])  # this one is definately needed! Without it the assert below does not work.
                self.tre_as_start.taxon_namespace.remove_taxon_label(leaf.taxon.label)
            else:
                for otu in self.concat_tips.keys():
                    if otu == leaf.taxon.label:
                        leaf.taxon.label = self.concat_tips[otu]
                        concat_tax.add(self.concat_tips[otu])
        # assert tree taxa in aln
        treed_taxa = set()
        for leaf in self.tre_as_start.leaf_nodes():
            treed_taxa.add(leaf.taxon.label)
        assert treed_taxa.issubset(concat_tax), ([item for item in treed_taxa if item not in concat_tax])

    def sp_to_keep(self):
        """Uses the sp_counter to make a list of sp that should be kept in concatenated alignment,
        because they are the only representative of the sp.

        Note: has test

        :return: dictionary with taxon name and number saying how many genes are missing
        """
        physcraper.debug("sp to keep")
        sp_to_keep = {}
        for tax_id in self.sp_counter:
            seq_counter = True
            not_present = 0
            for gene in self.sp_counter[tax_id]:
                if self.sp_counter[tax_id][gene] == 0:
                    seq_counter = False
                    not_present += 1
            if not seq_counter:
                sp_to_keep[tax_id] = not_present
        # physcraper.debug(sp_to_keep)
        return sp_to_keep

    def select_rnd_seq(self, tax_id, gene, del_acc):
        """Select a random seq from spn and gene to combine it with a random other one from another gene,
        but same spn. Is used if the user does not give a concatenation input file.

        Note: has test

        :param tax_id: taxon id
        :param gene:  gene name
        :param del_acc: dictionary that contains gene name: dict(spn: concat_id of random seq)
        :return: del_acc
        """
        physcraper.debug("select_rnd_seq")
        physcraper.debug(tax_id)
        physcraper.debug(gene)
        count = 2
        random_gen = random.choice(list(self.tmp_dict[tax_id][gene]))
        self.sp_acc_comb[tax_id][gene][random_gen]["concat:status"] = "used in concat"
        seq = str(self.tmp_dict[tax_id][gene][random_gen]["seq"])
        tax_id_ = str(tax_id)  # .replace(" ", "_")
        if gene in self.comb_seq.keys():
            # physcraper.debug(self.comb_seq[gene].keys())
            if tax_id_ not in self.comb_seq[gene].keys():
                physcraper.debug("taxid not present")
                # TODO: write check that for every tax_id, we add something to each comb_seq[gene]
                self.comb_seq[gene][tax_id_] = seq
                if gene in self.comb_acc:
                    self.comb_acc[gene][tax_id_] = random_gen
                else:
                    self.comb_acc[gene] = {tax_id_: random_gen}
                if gene in del_acc.keys():
                    if tax_id_ not in del_acc[gene].keys():
                        del_acc[gene][tax_id] = random_gen
                else:
                    del_acc[gene] = {tax_id: random_gen}
            else:
                physcraper.debug("tax_id present")
                tax_id_new = "{}_{}".format(tax_id_, count)
                while tax_id_new in self.comb_seq[gene].keys():
                    count += 1
                    tax_id_new = "{}_{}".format(tax_id_, count)
                physcraper.debug(tax_id_new)
                self.comb_seq[gene][tax_id_new] = seq
                self.comb_acc[gene][tax_id_new] = random_gen
                self.sp_acc_comb[tax_id][gene][random_gen]["new tipname"] = tax_id_new
                if gene in del_acc.keys():
                    if tax_id_ not in del_acc[gene].keys():
                        del_acc[gene][tax_id] = random_gen
                    else:
                        del_acc[gene][tax_id] = random_gen
                else:
                    del_acc[gene] = {tax_id: random_gen}
        else:
            physcraper.debug("in else")
            self.comb_seq[gene] = {tax_id_: seq}
            self.comb_acc[gene] = {tax_id_: random_gen}
            if gene in del_acc.keys():
                if tax_id_ not in del_acc[gene].keys():
                    del_acc[gene][tax_id] = random_gen
                else:
                    del_acc[gene] = {tax_id: random_gen}
            else:
                del_acc[gene] = {tax_id: random_gen}
        # # make sure all are of same length
        # does not work, assert crashes...
        # len_gene = []
        # for gen in self.comb_seq.keys():
        #     gene_taxid = (self.comb_seq[gen].keys())
        #     len_gene.append(gene_taxid)
        # # print(len_gene)
        # # for item in range(0, (len(len_gene) - 1)):
        #     # print(len_gene[item])
        # #   assert len_gene[item] == len_gene[item + 1]
        self.otu_to_spn(tax_id, gene, del_acc[gene][tax_id])
        return del_acc

    def otu_to_spn(self, tax_id, gene, random_gen):
        """ Makes a dict that contains the original tip labels from the starting tree,
        and the name it needs to have (no name duplicates allowed for many phylogenetic programs).
        This dict will be used in rename_drop_tips to rename or remove the tips.
        As such it is a helper function to produce the correct starting tree, for the concatenation run.

        :param tax_id: species name for concat
        :param gene: gene
        :param random_gen: the corresponding otu
        :return: self.concat_tips
        """
        if self.tre_start_gene == gene:
            # physcraper.debug(self.sp_acc_comb.keys())
            former_otu = self.sp_acc_comb[tax_id][gene][random_gen]['original_PS_id']
            for otu in self.tre_as_start.taxon_namespace:
                if otu.label == former_otu:
                    if "new tipname" in self.sp_acc_comb[tax_id][gene][random_gen]:
                        tax_id_concat = self.sp_acc_comb[tax_id][gene][random_gen]["new tipname"]
                    else:
                        tax_id_concat = tax_id
                    self.concat_tips[otu.label] = tax_id_concat
        return self.concat_tips

    def make_empty_seq(self, tax_id, gene):
        """Is called when there is no seq for one of the genes, but otu shall be kept in aln.
        Dendropy needs same taxon_namespace and number otu's for concatenation. It will just make an empty sequence of
        the same length.
        """
        # physcraper.debug("make_empty_seq")
        len_gene_aln = 0
        for tax, seq in self.single_runs[gene].aln.items():
            len_gene_aln = len(seq)
            break
        assert len_gene_aln != 0
        empty_seq = "?" * len_gene_aln
        # physcraper.debug([gene, tax_id])
        if gene in self.comb_seq:
            self.comb_seq[gene][str(tax_id)] = empty_seq
        else:
            self.comb_seq[gene] = {str(tax_id): empty_seq}

    def rm_rnd_sp(self, del_acc):
        """Removes the random selected seq from the tmp_dict, so that it cannot be selected again.
        """
        physcraper.debug("rm_rnd sp")
        for tax_id2 in self.tmp_dict:
            for gene2 in self.tmp_dict[tax_id2]:
                if gene2 in del_acc:
                    if tax_id2 in del_acc[gene2]:
                        key = del_acc[gene2][tax_id2]
                        if key in self.tmp_dict[tax_id2][gene2]:
                            del self.tmp_dict[tax_id2][gene2][key]

    def rm_empty_spn_entries(self, del_acc):
        """Removes keys from tmp dict, if the key/sp has no value anymore. Helper function.
        """
        physcraper.debug("rm_empty_spn_entries")
        del_taxid = None
        for tax_id2 in self.tmp_dict:
            for gene2 in self.tmp_dict[tax_id2]:
                if gene2 in del_acc:
                    if tax_id2 in del_acc[gene2]:
                        if len(self.tmp_dict[tax_id2][gene2]) == 0:
                            del_taxid = tax_id2
        if del_taxid is not None:
            for item in self.sp_acc_comb[del_taxid]:
                for otu in self.sp_acc_comb[del_taxid][item]:
                    if self.sp_acc_comb[del_taxid][item][otu]["concat:status"] != "used in concat":
                        self.sp_acc_comb[del_taxid][item][otu][
                            "concat:status"] = "deleted, because not enough seq are present"
            del self.tmp_dict[del_taxid]

    def make_alns_dict(self):
        """Makes dendropy aln out of dict self.comb_seq for all genes.
        """
        physcraper.debug("make_alns_dict")
        firstelement = True
        count = 0
        for gene in self.comb_seq.keys():
            physcraper.debug(gene)
            # physcraper.debug(self.comb_seq[gene].keys())
            if count == 0:
                len1 = len(self.comb_seq[gene].keys())
                len2 = len1
                count = 1
            else:
                len2 = len(self.comb_seq[gene].keys())
            assert len1 == len2
            # physcraper.debug([len1, len2])
        for gene in self.comb_seq.keys():
            physcraper.debug(count)
            if firstelement:
                aln1 = DnaCharacterMatrix.from_dict(self.comb_seq[gene])
                firstelement = False
                self.aln_all[count] = aln1
            else:
                aln = DnaCharacterMatrix.from_dict(self.comb_seq[gene], taxon_namespace=aln1.taxon_namespace)
                self.aln_all[count] = aln
            count += 1
        # self.dump('make_aln.p')

    def concatenate_alns(self):
        """Concatenate all alns into one aln.
        """
        physcraper.debug("concat alns")
        count = 0
        for gene in self.aln_all:
            if count == 0:
                aln1 = self.aln_all[gene]
                aln1.write(path="{}/aln1.fas".format(self.workdir), schema="fasta")
                count = 1
            else:
                aln2 = self.aln_all[gene]
                count += 1
                aln2.write(path="{}/aln{}.fas".format(self.workdir, count), schema="fasta")
                assert aln1.taxon_namespace == aln2.taxon_namespace
                len_aln1 = 0
                len_aln2 = 0
                for tax, seq in aln1.items():
                    len_aln1 += 1
                for tax, seq in aln2.items():
                    len_aln2 += 1
                assert len_aln1 == len_aln2, (len_aln1, len_aln2)
                aln1 = DnaCharacterMatrix.concatenate([aln1, aln2])
        aln1.write(path="{}/concat.fas".format(self.workdir),
                   schema="fasta")
        self.concatenated_aln = aln1

    def get_short_seq_from_concat(self, percentage=0.37):
        """Finds short sequences, all below a certain threshold will be removed,
        to avoid having really low coverage in the aln. Default = 0.37.

        Note percentage is a bit misleading, the cutoff is 37% of the whole concatenated
        alignment, but the sequences length is calculated without gaps present.
        The default is so low, as I want to keep taxa that have only a single locus
        and which is not the longest among the loci within the aln.
        """
        physcraper.debug("get_short_seq_from_concat")
        seq_len = {}
        num_tax = 0
        for tax, seq in self.concatenated_aln.items():
            seq = seq.symbols_as_string().replace("-", "").replace("?", "")
            seq_len[tax] = len(seq)
            num_tax += 1
        total_len = 0
        for tax, seq in self.concatenated_aln.items():
            total_len = len(seq)
            break
        assert total_len != 0, ("total len is not zero: '%s'" % total_len)
        min_len = total_len * percentage
        prune_shortest = []
        for tax, len_seq in seq_len.items():
            if len_seq < min_len:
                prune_shortest.append(tax)
        self.short_concat_seq = prune_shortest

    def remove_short_seq(self):
        """Removes short seq that were found with get_short_seq
        and write it to file.
        """
        physcraper.debug("remove_short_seq")
        self.concatenated_aln.remove_sequences(self.short_concat_seq)
        for leaf in self.tre_as_start.leaf_nodes():
            for tax in self.short_concat_seq:
                if tax.label == leaf.taxon.label:
                    self.tre_as_start.prune_taxa([leaf])
                    self.tre_as_start.prune_taxa_with_labels([leaf.label])
                    self.tre_as_start.prune_taxa_with_labels([leaf])
                    self.tre_as_start.prune_taxa_with_labels([leaf.taxon.label])
                    self.tre_as_start.taxon_namespace.remove_taxon_label(leaf.taxon.label)
        tre_as_start_str = self.tre_as_start.as_string(schema="newick",
                                                       # preserve_underscores=True,
                                                       unquoted_underscores=True,
                                                       suppress_rooting=True)
        fi = open("{}/{}".format(self.workdir, "starting_red.tre"), "w")
        fi.write(tre_as_start_str)
        fi.close()
        for tax in self.concatenated_aln.taxon_namespace:
            tax.label = tax.label.replace(" ", "_")
        self.concatenated_aln.write(path="{}/{}".format(self.workdir, "concat_red.fasta"), schema="fasta")
        tre_ids = set()
        for tax in self.tre_as_start.taxon_namespace:
            tre_ids.add(tax.label)
        aln_ids = set()
        for tax in self.concatenated_aln.taxon_namespace:
            aln_ids.add(tax.label)

    def make_concat_table(self):
        """ Makes a table that shows which gi numbers were combined.
        """
        if self.concatfile is None:
            genel = []
            taxid_l = {}
            for gene in self.comb_acc:
                genel.append(gene)
                for tax_id in self.comb_acc[gene]:
                    concat_id = self.comb_acc[gene][tax_id]
                    multiname = False
                    if len(tax_id.split("_")) >= 3:
                        tmp_taxid = "{}_{}".format(str(tax_id).split("_")[0], str(tax_id).split("_")[1])
                        multiname = True
                    if multiname:
                        if tmp_taxid in self.sp_acc_comb.keys():
                            unique_id = self.sp_acc_comb[tmp_taxid][gene][concat_id]["unique_id"]
                        else:
                            unique_id = self.sp_acc_comb[str(tax_id)][gene][concat_id]["unique_id"]
                    else:
                        unique_id = self.sp_acc_comb[str(tax_id)][gene][concat_id]["unique_id"]
                    if tax_id in taxid_l.keys():
                        taxid_l[tax_id].append(unique_id)
                    else:
                        taxid_l[tax_id] = [unique_id]
            with open("{}/concatenation.csv".format(self.workdir), "w") as csv_file:
                writer = csv.writer(csv_file)
                writer.writerow(genel)
                for key, value in taxid_l.items():
                    writer.writerow([key, value])

    def write_partition(self):
        """Write the partitioning file for RAxML.
        """
        physcraper.debug("write_partition")
        count = 0
        len_gene = 0
        for gene in self.single_runs:
            for tax, seq in self.single_runs[gene].aln.items():
                len_gene = len(seq.symbols_as_string())
                break
            if count == 0:
                with open("{}/partition".format(self.workdir), "w") as partition:
                    partition.write("DNA, {} = 1-{}\n".format(gene, len_gene))
                self.part_len = len_gene
                count = 1
            else:
                start = self.part_len + 1
                end = self.part_len + len_gene
                self.part_len = self.part_len + len_gene
                with open("{}/partition".format(self.workdir), "a") as partition:
                    partition.write("DNA, {} = {}-{}\n".format(gene, start, end))

    def place_new_seqs(self, num_threads=None):
        """Places the new seqs (that are only found in loci which is not the starting tree)
        onto one of the single run trees.
        """
        physcraper.debug("place_new_seqs")
        if len(self.concatenated_aln.taxon_namespace)-len(self.short_concat_seq) > len(self.tre_as_start.leaf_nodes()):
            if os.path.exists("RAxML_labelledTree.PLACE"):
                os.rename("RAxML_labelledTree.PLACE", "RAxML_labelledTreePLACE.tmp")

            with physcraper.cd(self.workdir):
                # cwd = os.getcwd()
                # os.chdir(self.workdir)
                physcraper.debug("make place-tree")
                try:
                    physcraper.debug("try")
                    num_threads = int(num_threads)
                    # debug(num_threads)
                    subprocess.call(["raxmlHPC-PTHREADS", "-T", "{}".format(num_threads), "-m", "GTRCAT",
                                     "-f", "v",  # "-q", "partition",
                                     "-s", "concat_red.fasta",
                                     "-t", "starting_red.tre",
                                     "-n", "PLACE"])
                except:
                    physcraper.debug("except")
                    subprocess.call(["raxmlHPC", "-m", "GTRCAT",
                                     "-f", "v",  # "-q", "partition",
                                     "-s", "concat_red.fasta",
                                     "-t", "starting_red.tre",
                                     "-n", "PLACE"])
                # os.chdir(cwd)
            physcraper.debug("read place tree")
            # # TODO MK CHRISTMAS: has non-labelled tree at the end, here might be the problem
            # placetre = Tree.get(path="{}/starting_red.tre".format(self.workdir),
            #                    schema="newick",
            #                    preserve_underscores=True,
            #                    suppress_internal_node_taxa=True, suppress_leaf_node_taxa=True)
            placetre = Tree.get(path="{}/RAxML_labelledTree.PLACE".format(self.workdir),
                                schema="newick",
                                preserve_underscores=True)
        else:
            placetre = Tree.get(path="{}/starting_red.tre".format(self.workdir),
                                schema="newick", preserve_underscores=True)
                                # suppress_internal_node_taxa=True, suppress_leaf_node_taxa=True)
        placetre.resolve_polytomies()
        physcraper.debug("rename place tree")
        for taxon in placetre.taxon_namespace:
            if taxon.label.startswith("QUERY"):
                taxon.label = taxon.label.replace("QUERY___", "")
            
        placetre.write(path="{}/place_resolve.tre".format(self.workdir), schema="newick", unquoted_underscores=True)

    def est_full_tree(self, num_threads=None):
        """Full raxml run from the placement tree as starting tree.
        """
        physcraper.debug("run full tree")
        with physcraper.cd(self.workdir):
            if os.path.exists("place_resolve.tre"):
                starting_fn = "place_resolve.tre"
            else:
                starting_fn = "starting_red.tre"
            if os.path.exists("concat_red.fasta.reduced") and os.path.exists("partition.reduced"):
                aln = "concat_red.fasta.reduced"
                partition = "partition.reduced"
            else:
                aln = "concat_red.fasta"
                partition = "partition"
            physcraper.debug([aln, starting_fn])
            try:
                num_threads = int(num_threads)
                if self.backbone is not True:
                    subprocess.call(["raxmlHPC-PTHREADS", "-T", "{}".format(num_threads), "-m", "GTRCAT",
                                     "-s", aln, "--print-identical-sequences",
                                     "-t", "{}".format(starting_fn),
                                     "-p", "1", "-q", partition,
                                     "-n", "concat"])
                else:
                    aln = "concat_red.fasta"
                    partition = "partition"
                    starting_fn = "place_resolve.tre"
                    subprocess.call(["raxmlHPC-PTHREADS", "-T", "{}".format(num_threads), "-m", "GTRCAT",
                                     "-s", aln, "--print-identical-sequences",
                                     "-r", "{}".format(starting_fn),
                                     "-p", "1", "-q", partition,
                                     "-n", "backbone_concat"])
            except:
                if self.backbone is not True:
                    subprocess.call(["raxmlHPC-PTHREADS", "-m", "GTRCAT",
                                     "-s", aln, "--print-identical-sequences",
                                     "-t", "{}".format(starting_fn),
                                     "-p", "1", "-q", partition,
                                     "-n", "concat"])
                else:
                    aln = "concat_red.fasta"
                    partition = "partition"
                    starting_fn = "place_resolve.tre"
                    subprocess.call(["raxmlHPC-PTHREADS", "-m", "GTRCAT",
                                     "-s", aln, "--print-identical-sequences",
                                     "-r", "{}".format(starting_fn),
                                     "-p", "1", "-q", partition,
                                     "-n", "backbone_concat"])

    def calculate_bootstrap(self, num_threads=None):
        """Calculate bootstrap and consensus trees.
        -p: random seed
        -s: aln file
        -n: output fn
        -t: starting tree
        -b: bootstrap random seed
        -#: bootstrap stopping criteria
        """
        physcraper.debug("calc bootstrap")
        with physcraper.cd(self.workdir):
            if os.path.exists("concat_red.fasta.reduced"):
                aln = "concat_red.fasta.reduced"
                partition = "partition.reduced"
            else:
                aln = "concat_red.fasta"
                partition = "partition"
            # run bootstrap
            # make bipartition tree
            # is the -f b command
            # -z specifies file with multiple trees
            try:
                num_threads = int(num_threads)
                subprocess.call(["raxmlHPC-PTHREADS", "-T", "{}".format(num_threads), "-m", "GTRCAT",
                                 "-s", aln, "-q", partition,
                                 "-p", "1", "-f", "a", "-x", "1", "-#", "autoMRE",
                                 "-n", "autoMRE_fa"])
                # strict consensus:
                subprocess.call(["raxmlHPC-PTHREADS", "-T", "{}".format(num_threads), "-m", "GTRCAT",
                                 "-J", "STRICT",
                                 "-z", "RAxML_bootstrap.autoMRE_fa",
                                 "-n", "StrictCon"])
                # majority rule:
                subprocess.call(["raxmlHPC-PTHREADS", "-T", "{}".format(num_threads), "-m", "GTRCAT",
                                 "-J", "MR",
                                 "-z", "RAxML_bootstrap.autoMRE_fa",
                                 "-n", "MR"])
            except:
                subprocess.call(["raxmlHPC", "-m", "GTRCAT",
                                 "-s", aln, "-q", partition,
                                 "-p", "1", "-f", "a", "-x", "1", "-#", "autoMRE",
                                 "-n", "autoMRE_fa"])
                # strict consensus:
                subprocess.call(["raxmlHPC", "-m", "GTRCAT",
                                 "-J", "STRICT",
                                 "-z", "RAxML_bootstrap.autoMRE_fa",
                                 "-n", "StrictCon"])
                # majority rule:
                subprocess.call(["raxmlHPC", "-m", "GTRCAT",
                                 "-J", "MR",
                                 "-z", "RAxML_bootstrap.autoMRE_fa",
                                 "-n", "MR"])

    def user_defined_concat(self):
        """If a user gave an input file to concatenate data. Fills in the data for self.comb_seq, self.comb_acc
        (is the replacement function for select_rnd_seq).
        """
        physcraper.debug("user_defined_concat")
        has_header = True
        with open("{}/{}".format(self.workdir, self.concatfile), mode="r") as infile:
            reader = csv.reader(infile)
            if has_header:
                # next(reader) 
                genel = reader.next()
            sp_concat = dict((rows[0], rows[1]) for rows in reader)
            physcraper.debug(sp_concat)
        for otu in sp_concat.keys():
            global_taxid = None
            concat_l = sp_concat[otu]
            if concat_l[:1] == "[":
                concat_l = concat_l[1:-1]
            concat_l = concat_l.split(", ")
            # physcraper.debug("FOR CONCAT_l")
            for seq_id in concat_l:
                # physcraper.debug(seq_id)
                gene_l = []
                if seq_id[:1] == "'":
                    seq_id = seq_id[1:-1]
                elif seq_id[:2] == "u'":
                    seq_id = seq_id[2:-1]
                else:
                    seq_id = seq_id[2:-1]  # TODO: prone to errors! because of unicode

                seq_id = seq_id.encode("utf-8")
                # physcraper.debug(seq_id)
                # if len(seq_id.split(".")) == 1:
                #     physcraper.debug(some)
                # if seq_id == u'S_parvifolius':
                #     physcraper.debug(some)
                for gene in genel:
                # for gene in self.single_runs:
                    physcraper.debug(gene)
                    tax_id = None
                    # filter to existing species
                    for key, val in self.single_runs[gene].otu_dict.items():
                        found = False
                        # only add the information of sequences that were added
                        if val['^physcraper:status'].split(' ')[0] not in self.seq_filter:
                            # print(seq_id)
                            # print(otu)
                            # print(len(self.comb_seq))
                            # print(key)
                            # print(seq_id)
                            # if u'^ot:originalLabel' in val:
                                # print(str(val[u'^ot:originalLabel']))
                                # print(str(seq_id))
                                # print(str(val[u'^ot:originalLabel']) == str(seq_id))
                                # print(type(str(val[u'^ot:originalLabel'])))
                                # print(type(str(seq_id)))
                            # physcraper.debug(val)
                            # if gene in self.comb_seq:
                            #     lcsb = len(self.comb_seq[gene])
                            # else:
                            #     lcsb = 0
                            # lgb = len(gene_l)
                            if len(seq_id.split(".")) >= 2:
                                if "^ncbi:accession" in val:
                                    if seq_id == val["^ncbi:accession"]:
                                        tax_id = "taxid_{}".format(val['^ncbi:taxon'])
                                        gene_l.append(gene)
                                        found = True
                                        physcraper.debug("found")
                                else:
                                    physcraper.debug("SOMETHING IS HAPPENING: no acc")
                            else:
                                # physcraper.debug(val)
                                if "^ncbi:accession" in val:
                                    if seq_id == val["^ncbi:accession"]:
                                        tax_id = "taxid_{}".format(val['^ncbi:taxon'])
                                        # gene_l.append(gene)
                                        found = True
                                        # physcraper.debug("found")
                                    # else:
                                    #     print("not same acc")
                                elif u'^ncbi:taxon' in val:
                                    if str(seq_id) == str(val[u'^ncbi:taxon']):
                                        tax_id = "taxid_{}".format(val[u'^ncbi:taxon'])
                                        # gene_l.append(gene)
                                        found = True
                                        # physcraper.debug("found")
                                    elif str(seq_id) == str(val['^user:TaxonName']) and val[u'^ncbi:taxon'] is not None:
                                        tax_id = "taxid_{}".format(val[u'^ncbi:taxon'])
                                        # gene_l.append(gene)
                                        found = True
                                        # physcraper.debug("found")
                                elif '^user:TaxonName' in val:
                                    if str(seq_id) == str(val['^user:TaxonName']):
                                        tax_id = "taxid_{}".format(val['^user:TaxonName'].replace("_", "").replace(" ", ""))
                                        found = True
                                        # physcraper.debug("found")
                                    # else:
                                        # physcraper.debug("not same orig label?")
                                else:
                                    physcraper.debug("SOMETHING IS HAPPENING")

                            if found:
                                gene_l.append(gene)
                                if tax_id is not None:
                                    tax_id = str(tax_id) 
                                    global_taxid = tax_id
                                    for key2, val2 in self.sp_acc_comb[tax_id][gene].items():
                                        cond = False
                                        physcraper.debug(val2)
                                        if len(seq_id.split(".")) >= 2 and val2["unique_id"] == seq_id:
                                            cond = True
                                        else:
                                            if val2["unique_id"] == seq_id:
                                                cond = True
                                        if cond:
                                            concat_id = key2
                                            self.sp_acc_comb[tax_id][gene][concat_id]["concat:status"] = "used in concat"
                                            seq = str(self.sp_acc_comb[tax_id][gene][concat_id]["seq"])
                                            otu_ = otu.replace(" ", "_")
                                            otu_ = otu_.replace(".", "").replace("'", "")
                                            if gene in self.comb_seq.keys():
                                                if otu_ not in self.comb_seq[gene].keys():
                                                    self.comb_seq[gene][otu_] = seq
                                                    if gene in self.comb_acc:
                                                        self.comb_acc[gene][otu_] = concat_id
                                                    else:
                                                        self.comb_acc[gene] = {otu_: concat_id}
                                                else:
                                                    self.comb_seq[gene][otu_] = seq
                                                    self.comb_acc[gene][otu_] = concat_id
                                        
                                            else:
                                                self.comb_seq[gene] = {otu_: seq}
                                                self.comb_acc[gene] = {otu_: concat_id}
                                            if tax_id != otu:
                                                self.sp_acc_comb[tax_id][gene][concat_id]["new tipname"] = otu_
                                            self.otu_to_spn(tax_id, gene, concat_id)
                                            # doer not work here
                                            # lga = len(gene_l)
                                            # assert lgb != lga
                                            # lcsa = len(self.comb_seq[gene])
                                            # assert lcsb != lcsa
                                            break
                                if tax_id is not None:
                                    break
                    physcraper.debug(len(self.comb_seq))
                    # if otu == "taxid_1129161":
                    #     print(some)
                    physcraper.debug(len(gene_l) == len(concat_l))
                    if len(gene_l) == len(concat_l):
                        missing_gene = [loci for loci in self.genes_present if loci not in gene_l]
                        for genes in missing_gene:
                            physcraper.debug(genes)
                            # self.make_empty_seq(global_taxid, genes)
                            self.make_empty_seq(otu_, genes)
                            # physcraper.debug(some)
            #     if seq_id == "u'S_parvifolius'" and found == True:
            #         physcraper.debug(some)
            # if otu == "taxid_1129161":
            #     physcraper.debug(some)
        # make sure all are of same length
        len_gene = []
        for gen in self.comb_seq.keys():
            gene_taxid = (self.comb_seq[gen].keys())
            len_gene.append(gene_taxid)
            # physcraper.debug(len_gene)
        for i in range(0, (len(len_gene) - 1)):
            # physcraper.debug(len_gene[i])
            assert len_gene[i] == len_gene[i + 1], ([seq_id for seq_id in len_gene[i] if seq_id not in len_gene[i+1]])

    def dump(self, filename="concat_checkpoint.p"):
        """ Save a concat run as pickle.
        """
        pickle.dump(self, open("{}/{}".format(self.workdir, filename), "wb"))

    def write_otu_info(self, downtorank=None):
        """Writes output tables to file: Makes reading important information less code heavy.

        file with all relevant GenBank info to file (otu_dict).

        It uses the self.sp_d to get sampling information, that's why the downtorank is required.

        :param downtorank: hierarchical filter
        :return: writes output to file
        """   
        physcraper.debug("write_otu_info")
        otu_dict_keys = [
            "unique_id", "sp_id", "original_PS_id", "concat:status"]
        with open("{}/otu_seq_info.csv".format(self.workdir), "w") as output:
            writer = csv.writer(output)
            writer.writerow(otu_dict_keys)
            # physcraper.debug(self.sp_acc_comb.keys())
            for otu in self.sp_acc_comb.keys():
                # physcraper.debug(self.sp_acc_comb[otu].keys())
                # rowinfo = spn_writer
                for loci in self.sp_acc_comb[otu].keys():
                    # physcraper.debug("newinfo")
                    rowinfo = [loci]
                    # physcraper.debug(self.sp_acc_comb[otu][loci])
                    for concat_id in self.sp_acc_comb[otu][loci].keys():
                        rowinfo_details = deepcopy(rowinfo)
                        # physcraper.debug(rowinfo_details)
                        rowinfo_details.append(concat_id)
                        for item in otu_dict_keys:
                            if item in self.sp_acc_comb[otu][loci][concat_id].keys():
                                tofile = str(self.sp_acc_comb[otu][loci][concat_id][item]).replace("_", " ")
                                rowinfo_details.append(tofile)
                            else:
                                rowinfo_details.append("-")
                        # physcraper.debug(rowinfo_details)
                        writer.writerow(rowinfo_details)                

