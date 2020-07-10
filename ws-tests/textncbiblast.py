import sys
import physcraper.AWSWWW as AWSWWW
import datetime

start = datetime.datetime.now()
sys.stderr.write("running a blast query against NCBI START {}".format(start))


query="ATATCAATAAGCGGAGGAAAAGAAACCAACAGGGATTGCCTCAGTAACGGCGAGTGAAGCGGCAACAGCTCAAATTTGAAATCTGGCCCTAGGCCCGAGTTGTAATTTGCAGAGGATGCTTCCGGTGCGGCGCCGTCCAAGTCCCCTGGAACGGGGTGCCACAGAGGGTGAGAGCCCCGTCGGGTCGGCCGCCAAGCCTATGTGAAGCTCCTTCGACGAGTCGAGTAGTTTGGGAATGCTGCTCTAAATGGGAGGTAGACCCCTTCTAAAGCTAAATATTGGCCAGAGACCGATAGCGCACAAGTAGAGTGATCGAAAGATGAAAAGCACTTTGAAAAGAGGGTTAAACAGTACGTGAAATTGTTGAAAGGGAAGCGCTTGTGACCAGACGTGCGCCGGGTGTTCAGCGGGCGTTCTCGCCCGTCTACTCGCCCTGGCGCAGGCCAGCGTCGGTTCGGATGGGTGGACAAAGGTACCAGGAACGTGGCTCCCTCGGGAGTGTTATAGCCTGGTGCGTCATGCCCCCGTCCGGACCGAGGTTCGCGCTCTGCAAGGACGCTGGCGTAATGGTCCCCAGCGGCCCGTCTTGAAACACGGACCAAGGAGTCGAGGTTTTGTGCGAGTGTCTGGGTGTCAAACCCGCACGCGTAATGAAAGTGAACGCAGGTGGGAGCTTCGGCGCACCACCGACCGATCCTGAAGTTTTCGGATGGATTTGAGTAAGAGCATAGGGCCTCGGACCCGAAAGATGGTGAACTATACTTGGATAGGGTGAAGCCAGAGGAAACTCTGGTGGAGGCTCGCAGCGGTTCTGACGTGCAAATCGATCGTCAAATCTGAGTATGGGGGCGAAAGACTAATCGAACCATCTAGTAGCTGGTTACCGCCGAAGTTTCCCTCAGGATAG"
result_handle = AWSWWW.qblast("blastn",
                               "nt",
                               query,
                               hitlist_size=2)


end = datetime.datetime.now()
sys.stderr.write("END time {}".format(end))
result_handle.close()


ncbi_id = 147538
query = query + "txid{}[orgn]) ".format(ncbi_id)



result_handle = AWSWWW.qblast("blastn",
                            "nt",
                            query,
                            url_base=self.config.url_base,
                            entrez_query=equery,
                            hitlist_size=self.config.hitlist_size,
                            num_threads=self.config.num_threads)