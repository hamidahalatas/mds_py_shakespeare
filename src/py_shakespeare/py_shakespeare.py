import json
import pandas as pd
import requests
from nltk.tokenize import sent_tokenize, word_tokenize
from textstat.textstat import textstatistics,legacy_round
from bs4 import BeautifulSoup
import re

class shake_play:
    def __init__(self, min_num_character = 20, **kwargs):
        assert isinstance(min_num_character, int), f"This function only works on integers"
        
        r = requests.get(f"https://dracor.org/api/corpora/shake/metadata")
        status = r.status_code
        if status==404:
            raise Exception("404 : error (failed to make request)")
        if status==500:
            raise Exception("500 : successfully made request but had internal error")
        else: 
            shake_meta = r.json()
            shake_meta_df = pd.DataFrame(shake_meta)
            # Revising some titles so it can be merged to genre table
            shake_meta_df['title'] = shake_meta_df['title'].apply(lambda s: s.removeprefix('A ').removeprefix('The ')).apply(lambda x: x.replace("’","'").replace("Labor","Labour").replace("Part 1","Part I").replace("Part 2","Part II").replace("Part 3","Part III").replace("About","about"))

            genre = pd.read_html('https://www.opensourceshakespeare.org/views/plays/plays_numwords.php')[1]
            genre = genre.rename(columns={0: "words", 1: "title", 2: "genre"}).drop(genre.index[0]).drop(['words'], axis=1)
            shake_merge = pd.merge(shake_meta_df, genre, how='outer', on=['title'])

            shake_merge['popularity'] = pd.qcut(shake_merge['wikipediaLinkCount'], 3, labels=["Low", "Medium", "High"]) 
            shake_merge['play_complexity'] = pd.qcut(shake_merge['averageDegree'], 3, labels=["Low", "Medium", "High"]) 
            shake_merge['play_length_hr'] = shake_merge['wordCountSp'].apply(lambda s: s/170/60)
            shake_merge['play_length'] = pd.qcut(shake_merge['play_length_hr'], 3, labels=["Low", "Medium", "High"]) 

            shake_merge = shake_merge.rename(columns={'numOfSpeakers': 'num_character',
                                                       'numOfSegments': 'num_scene',
                                                       'numOfSpeakersUnknown': 'num_unknown_character',
                                                       'numOfSpeakersMale': 'num_male_character',
                                                       'numOfSpeakersFemale': 'num_female_character',
                                                       'numOfSpeakersFemale': 'num_female_character'})

            shake_merge = shake_merge[(shake_merge['num_character'] >= min_num_character)]
           
            if 'play_length' in kwargs:
                assert kwargs["play_length"] in ["Low", "Medium", "High"], "This type of play length is not available. Try 'Low', 'Medium', or 'High'"         
                shake_merge = shake_merge[(shake_merge['play_length'] == kwargs.get('play_length'))]
                
            if 'play_complexity' in kwargs:
                assert kwargs["play_complexity"] in ["Low", "Medium", "High"], "This type of play complexity is not available. Try 'Low', 'Medium', or 'High'"         
                shake_merge = shake_merge[(shake_merge['play_complexity'] == kwargs.get('play_complexity'))]
                
            self.df = shake_merge
            self.df = self.df.sort_values(by='wikipediaLinkCount', ascending=False, ignore_index = True)

    def get_summary(self):
        summary = ["title", "popularity", "genre", "num_character", "play_length", "play_complexity"]
        filtered = self.df[summary]
        return filtered

    def get_complete(self):
        data = ["title", "popularity", "genre", "num_male_character", "num_female_character", "num_unknown_character", "num_scene", "play_complexity", "play_length_hr"]
        filtered = self.df[data]
        return filtered
    
    def get_script(self, row = 1):
        assert row<=len(self.df.index), f"Selected row is out of range"
        shake_merge = self.df
        playname = shake_merge.loc[row-1,'name']
        script = requests.get(f"https://dracor.org/api/corpora/shake/play/{playname}/tei")
        with open(f'{playname}_script.xml', 'wb') as f:
            f.write(script.content)
        print("Your script is saved as xml document")
    

class shake_monologue:
    def __init__(self, gender = "ALL", min_line = 30, include_all = True, **kwargs):
        
        assert gender in ["ALL", "FEMALE", "MALE"], "Input of gender should be 'ALL', 'FEMALE', or 'MALE'"
        assert min_line>0, "Minimum line of monologue should be positive"
    
        dict = {'folger' : ["AWW","Ant","AYL","Err","Cor","Cym","Ham","1H4","2H4","H5","1H6","2H6","3H6","H8","JC","Jn","Lr","LLL","Mac","MM","MV","Wiv","MND","Ado","Oth","Per","R2","R3","Rom","Shr","Tmp","Tim","Tit","Tro","TN","TGV","WT"],
                'play' : ["all-s-well-that-ends-well","antony-and-cleopatra","as-you-like-it","the-comedy-of-errors","coriolanus","cymbeline","hamlet","henry-iv-part-i","henry-iv-part-ii","henry-v","henry-vi-part-1","henry-vi-part-2","henry-vi-part-3","henry-viii","julius-caesar","king-john","king-lear","love-s-labor-s-lost","macbeth","measure-for-measure","the-merchant-of-venice","the-merry-wives-of-windsor","a-midsummer-night-s-dream","much-ado-about-nothing","othello","pericles","richard-ii","richard-iii","romeo-and-juliet","the-taming-of-the-shrew","the-tempest","timon-of-athens","titus-andronicus","troilus-and-cressida","twelfth-night","two-gentlemen-of-verona","the-winter-s-tale"]}
                
        folger_table = pd.DataFrame.from_dict(dict)

        if include_all == True:
            shake_all_name = folger_table['play']
        else:
            play_list = kwargs.get('play_list')
            assert play_list != None, "If include_all = False, you should pass a list of Folger code for plays"
            shake_all_name = folger_table["play"][folger_table['folger'].isin(play_list)]
            
        cast_table = pd.DataFrame(columns = ['play', 'name', 'gender', 'degree'])

        for x in shake_all_name:
            r = requests.get(f"https://dracor.org/api/corpora/shake/play/{x}/cast")
            if r.status_code==404:
                raise Exception("404 : error (failed to make request)")
            if r.status_code==500:
                raise Exception("500 : successfully made request but had internal error")
            else:
                cast = r.json()
                cast = pd.DataFrame(cast)
                if gender == "ALL":
                    cast = cast[(cast['isGroup'] == False)]
                else:
                    cast = cast[(cast['isGroup'] == False) & ((cast['gender'] == gender) | (cast['gender'] == "UNKNOWN") | (cast['gender'].isnull()))] 
                cast['play'] = x
                cast = cast[["play", "name", "gender", "degree"]]
                cast_table = pd.concat([cast_table, cast], ignore_index=True)

        cast_table_merge = pd.merge(cast_table, folger_table, how='inner', on=['play'])

        folger_name = list(cast_table_merge.folger.unique())

        mono_table = pd.DataFrame(columns = ['name', 'monologue_link', 'line_num'])

        for x in folger_name:
            r = requests.get(f"https://www.folgerdigitaltexts.org/{x}/monologue/{min_line}")
            if r.status_code==200:
                soup = BeautifulSoup(r.text, "html.parser")
                raw_text = soup.find_all("a")
                link = [link.get('href') for link in raw_text]
                charact = [re.findall('(.*?)\s*\((.*?)\)', strong_tag.previous_sibling)[0][0] for strong_tag in raw_text]
                line_num = [re.findall('(.*?)\s*\((.*?)\)', strong_tag.previous_sibling)[0][1] for strong_tag in raw_text]
                mon = {'name':charact,'monologue_link':link, 'line_num': line_num}
                mon_df = pd.DataFrame(mon)
                mono_table = pd.concat([mono_table, mon_df], ignore_index=True)

        self.df = pd.merge(cast_table, mono_table, how='inner', on=['name'])
        self.df = self.df.sort_values(by=['degree', 'line_num'], ascending=False, ignore_index=True)
   
    def get_summary(self): 
        summary = self.df
        return summary
    
    def get_complexity(self):        
        for i in range(len(self.df)):
            url = self.df["monologue_link"][i]
            r = requests.get(url)
            
            if r.status_code==200:
                soup = BeautifulSoup(r.text, "html.parser")
                text = soup.text
                text = text.replace('\n', '')

                sentences = sent_tokenize(text)
                sentence_count = len(sentences)
                words = word_tokenize(text)
                word_count = len(words)
                average_sentence_length = float(word_count / sentence_count) 

                syllable = textstatistics().syllable_count(text)
                ASPW = float(syllable)/float(word_count)
                ASPW = legacy_round(ASPW, 1)

                FRE = float(0.39 * average_sentence_length) + float(11.8 * ASPW) - 15.59
                self.df.loc[self.df.index[i], 'complexity_score'] = round(FRE,2)
        
        self.df['complexity_category'] = pd.cut(x=self.df['complexity_score'], bins=[1, 6, 12, 18, 400],
                                         labels=['Basic', 'Average', 'Skilled', 'Advanced'])
        
        complex = self.df
        return complex
    
    def get_script(self, row = 1):
        assert row<=len(self.df.index), f"Selected row is out of range"
        
        script = self.df
        url = script["monologue_link"][row-1]
        play = script["play"][row-1]
        name = script["name"][row-1]        
        script = requests.get(url)
        soup = BeautifulSoup(script.text, "html.parser")
        
        with open(f'{play}_{name}_monologue.txt', 'wt', encoding='utf-8') as f:
            f.write(soup.text)
        print("Your monologue script is saved as txt document")
    