import json
import pandas as pd
import requests
from nltk.tokenize import sent_tokenize, word_tokenize
from textstat.textstat import textstatistics,legacy_round
from bs4 import BeautifulSoup
import re

class shake_play:
    """
    Base class to obtain the list of Shakespeare play based on minimum number of character, length of the play, and complexity of the play. This class will obtain data from DraCor API and merge the data to genre of Shakespeare play that was obtained by scraping "www.opensourceshakespeare.org" website.
    
    Attributes
    ----------
    min_num_character : int
      Minimum number of characters in the play.
    play_length : str, optional
      Relative length of the play category: Low, Medium, or High.
    play_complexity : str, optional
      Relative complexity of the play category: Low, Medium, or High.
      
    Examples
    --------
    >>> from py_shakespeare import py_shakespeare
    >>> play = py_shakespeare.shake_play(min_num_character = 40, play_length = "Medium")
    >>> print(play)
    >>> <__main__.shake_play object at 0x11f6776a0>
    """
    
    def __init__(self, min_num_character = 20, **kwargs):

        assert isinstance(min_num_character, int), f"This function only works on integers"
        
        r = requests.get("https://dracor.org/api/corpora/shake/metadata")
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
           
            # based on literature review saying that play speech usually is 170 words per minute
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
        """
        Obtain summary table of the class obtained from shake_play() function.
        
        Returns
        -------
        pandas.core.frame.DataFrame
          A dataframe containing summarized information of Shakespeare plays from the class. The variables in this table include:
              * title: title of the play
              * popularity: relative popularity (from the number of Wikipedia links referring to this play) to other plays with similar minimum number of character
              * genre: genre of the play (based on Open Source Shakespeare website)
              * num_character: number of character/cast in this play
              * play_length: relative length of the play to other plays with similar minimum number of character. Obtained by using number of words variable divided by rate of speech in a drama (170 words per minute)
              * play_complexity: relative complexity of the play to other plays with similar minimum number of character. Obtained by using average degree of dialogue between each character in the play

        Examples
        --------
        >>> from py_shakespeare import py_shakespeare
        >>> play = py_shakespeare.shake_play(min_num_character = 40, play_length = "Medium")
        >>> play.get_summary()
         	title	popularity	genre	num_character	play_length	play_complexity
        0	Henry VIII	Low	History	48	Medium	Low
        1	Henry VI, Part III	Low	History	49	Medium	Medium
        """
        
        summary = ["title", "popularity", "genre", "num_character", "play_length", "play_complexity"]
        filtered = self.df[summary]
        return filtered

    def get_complete(self):
        """
        Obtain summary table of the class obtained from shake_play() function.
        
        Returns
        -------
        pandas.core.frame.DataFrame
          A dataframe containing complete information of Shakespeare plays from the class. The variables in this table are information in the summary table added by:
              * num_male_character: number of male character/cast in this play
              * num_female_character: number of female character/cast in this play
              * num_unknown_character: number of unknown gender character/cast in this play
              * num_scene: number of scene/segment in this play
              * play_length_hr: length of the play in hours. Obtained by using number of words variable divided by rate of speech in a drama (170 words per minute)

        Examples
        --------
        >>> from py_shakespeare import py_shakespeare
        >>> play = py_shakespeare.shake_play(min_num_character = 40, play_length = "Medium")
        >>> play.get_complete()
         	title	popularity	genre	num_male_character	num_female_character	num_unknown_character	num_scene	play_complexity	play_length_hr
        0	Henry VIII	Low	History	33	4	5	18	Low	2.454804
        1	Henry VI, Part III	Low	History	26	2	8	28	Medium	2.478039
        """

        data = ["title", "popularity", "genre", "num_male_character", "num_female_character", "num_unknown_character", "num_scene", "play_complexity", "play_length_hr"]
        filtered = self.df[data]
        return filtered
    
    def get_script(self, row = 1):
        """
        Download xml script of the selected play.
        
        Parameters
        ----------
        row : int
          Position of the play from the table which script we want to obtained (start from 1).
        
        Returns
        -------
        str
          information that your data has been downloaded in your folder

        Examples
        --------
        >>> from py_shakespeare import py_shakespeare
        >>> play = py_shakespeare.shake_play(min_num_character = 40, play_length = "Medium")
        >>> play.get_script(row = 2)
        Your script is saved as xml document
        """

        assert row<=len(self.df.index), f"Selected row is out of range"
        shake_merge = self.df
        playname = shake_merge.loc[row-1,'name']
        script = requests.get(f"https://dracor.org/api/corpora/shake/play/{playname}/tei")
        with open(f'{playname}_script.xml', 'wb') as f:
            f.write(script.content)
        print("Your script is saved as xml document")
    

    
class shake_monologue:
    """
    Base class to obtain a list of monologues from Shakespeare plays based on gender of the monologues speaker, minimum line of monologue, and list of plays which monologues want to be obtained. This class will obtain data from both DraCor and The Folger Shakespeare API to help user choose monologue based on several inputs.
    
    Attributes
    ----------
    gender : str
      Gender of the monologues speaker: ALL, UNKNOWN, MALE, or FEMALE.
    min_line : int
      Number of minimum line in the monologue
    include_all : bool
      Whether we want to include all plays from Shakespeare or not. WARNING: choosing True might result in a long wait for the function to run.
    play_list : arrays, optional
      Array of Folger id of plays we want to be included in the search for monologues. List of Folger id can be found below:
          * **AWW**: All's Well That Ends Well
          * **Ant**: Antony and Cleopatra
          * **AYL**: As You Like It
          * **Err**: The Comedy of Errors
          * **Cor**: Coriolanus
          * **Cym**: Cymbeline
          * **Ham**: Hamlet
          * **1H4**: Henry IV, Part 1
          * **2H4**: Henry IV, Part 2
          * **H5**: Henry V
          * **1H6**: Henry VI, Part 1
          * **2H6**: Henry VI, Part 2
          * **3H6**: Henry VI, Part 3
          * **H8**: Henry VIII
          * **JC**: Julius Caesar
          * **Jn**: King John
          * **Lr**: King Lear
          * **LLL**: Love's Labor's Lost
          * **Mac**: Macbeth
          * **MM**: Measure for Measure
          * **MV**: The Merchant of Venice
          * **Wiv**: The Merry Wives of Windsor
          * **MND**: A Midsummer Night's Dream
          * **Ado**: Much Ado About Nothing
          * **Oth**: Othello
          * **Per**: Pericles
          * **R2**: Richard II
          * **R3**: Richard III
          * **Rom**: Romeo and Juliet
          * **Shr**: The Taming of the Shrew
          * **Tmp**: The Tempest
          * **Tim**: Timon of Athens
          * **Tit**: Titus Andronicus
          * **Tro**: Troilus and Cressida
          * **TN**: Twelfth Night
          * **TGV**: Two Gentlemen of Verona
          * **TNK**: Two Noble Kinsmen
          * **WT**: The Winter's Tale

    Examples
    --------
    >>> from py_shakespeare import py_shakespeare
    >>> ml = shake_monologue(gender = "ALL", min_line = 30, include_all = False, play_list = ["Rom", "Ham"])
    >>> print(ml)
    >>> <__main__.shake_monologue object at 0x11ff41ac0>
    """

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

        """
        Obtain summary table of the class obtained from shake_monologue() function.
        
        Returns
        -------
        pandas.core.frame.DataFrame
          A dataframe containing summarized information of Shakespeare plays from the class. The variables in this table include:
              * play: title of the play
              * name: name of the character
              * gender: gender of the character
              * degree: how many other characters this character interacted with
              * monologue_link: Link to the monologue
              * line_num: number of lines of the monologue

        Examples
        --------
        >>> from py_shakespeare import py_shakespeare
        >>> ml = shake_monologue(gender = "ALL", min_line = 40, include_all = False, play_list = ["Rom", "Ham"])
        >>> ml.get_summary()
        	play	name	gender	degree	monologue_link	line_num
        0	romeo-and-juliet	Romeo	MALE	31	http://www.folgerdigitaltexts.org/Rom/segment/...	47
        1	hamlet	Hamlet	None	29	http://www.folgerdigitaltexts.org/Ham/segment/...	60
        2	romeo-and-juliet	Juliet	FEMALE	21	http://www.folgerdigitaltexts.org/Rom/segment/...	46
        3	romeo-and-juliet	Friar Lawrence	MALE	18	http://www.folgerdigitaltexts.org/Rom/segment/...	51
        4	romeo-and-juliet	Friar Lawrence	MALE	18	http://www.folgerdigitaltexts.org/Rom/segment/...	41
        5	romeo-and-juliet	Mercutio	MALE	10	http://www.folgerdigitaltexts.org/Rom/segment/...	43
        6	hamlet	The Ghost	None	5	http://www.folgerdigitaltexts.org/Ham/segment/...	50
        """

        summary = self.df
        return summary
    
    def get_complexity(self):
        
        """
        Obtain table of the class obtained from shake_monologue() function plus the complexity of each monologue. Complexity score were calculated using `Flesch Kincaid Grade readibility score <https://readable.com/readability/flesch-reading-ease-flesch-kincaid-grade-level/>`_
        
        Returns
        -------
        pandas.core.frame.DataFrame
          A dataframe containing complete information of Shakespeare plays from the class. The variables in this table are information in the summary table added by:
              * complexity_score: Flesch Kincaid Grade readibility score
              * complexity_category: Complexity category based on the readibility score

        Examples
        --------
        >>> from py_shakespeare import py_shakespeare
        >>> ml = shake_monologue(gender = "ALL", min_line = 40, include_all = False, play_list = ["Rom", "Ham"])
        >>> ml.get_complexity()
        	play	name	gender	degree	monologue_link	line_num	complexity_score	complexity_category
        0	romeo-and-juliet	Romeo	MALE	31	http://www.folgerdigitaltexts.org/Rom/segment/...	47	7.55	Average
        1	hamlet	Hamlet	None	29	http://www.folgerdigitaltexts.org/Ham/segment/...	60	6.70	Average
        2	romeo-and-juliet	Juliet	FEMALE	21	http://www.folgerdigitaltexts.org/Rom/segment/...	46	16.88	Skilled
        3	romeo-and-juliet	Friar Lawrence	MALE	18	http://www.folgerdigitaltexts.org/Rom/segment/...	51	19.13	Advanced
        4	romeo-and-juliet	Friar Lawrence	MALE	18	http://www.folgerdigitaltexts.org/Rom/segment/...	41	24.53	Advanced
        5	romeo-and-juliet	Mercutio	MALE	10	http://www.folgerdigitaltexts.org/Rom/segment/...	43	70.50	Advanced
        6	hamlet	The Ghost	None	5	http://www.folgerdigitaltexts.org/Ham/segment/...	50	24.44	Advanced        
        """

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
        """
        Download txt script of the selected monologue.
        
        Parameters
        ----------
        row : int
          Position of the monologue from the table which script we want to obtained (start from 1).
        
        Returns
        -------
        str
          information that your data has been downloaded in your folder

        Examples
        --------
        >>> from py_shakespeare import py_shakespeare
        >>> ml = shake_monologue(gender = "ALL", min_line = 40, include_all = False, play_list = ["Rom", "Ham"])
        >>> ml.get_script(row = 2)
        Your monologue script is saved as txt document
        """

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
    