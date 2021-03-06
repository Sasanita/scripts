
#!/bin/bash#!/bin/bash


SRILM=/home/alvaro/smt/software/srilm/bin/i686-m64
THOT=/usr/local/bin/

usage(){
    echo "Usage: combine_systems.sh -i <string> -lm <string> -o <string> [-order <int>] [-giza <string> ] [-ibm1 <string>] [-tmp <string>] [-debug] [-v]"
    echo " -i <string>       : Input file"
    echo " -lm  <string>     : ARPA n-gram language model (default 5)"
    echo " -o  <string>      : Output file"
    echo " -order  <string>  : Order of the n-gram "
    echo " -giza <file>      : Use Giza alignments from this input file (original source file)"
    echo " -tmp  <string>    : Temporal directory (default /tmp)"
    echo " -src_trg <string> : source -> target giza files' prefix (if we use Giza alignments)"
    echo " -src  <string>    : source files' prefix (if we use Giza alignments)"
    echo " -trg  <string>    : target giza files' prefix (if we use Giza alignments)"
    echo " -ibm1             : IBM1 model (statistical dictionary) (python script)" 
    echo " -lambda           : Interpolation factor (default 0.5)" 
    echo " -debug            : Do not remove temporal files" 
    echo " -v                : Verbose mode" 
}



clean(){
    rm -rf  ${tmp}
}

launch_align_GIZA(){

IFS=''
i=0
echo -n "" > $output
echo "Using GIZA alginments. Input file: ${src_file}"
while read -r -u 2 sentence && read -r -u 3 src_sentence ;
do
    #echo "${sentence} =============================== ${src_sentence}"

    # Extract the words which originated the UNK from the sentence
    echo "${sentence}" | grep  "UNK" -o |cut -d _ -f 2 > ${tmp}/unk_words
    echo "${src_sentence}" > ${tmp}/src_sent
    edited_sentence=`echo ${sentence}`
    i=`echo ${i}+1 |bc -l`
    echo "Reading sentence ${i}"
    n_unks=`wc -l ${tmp}/unk_words | awk '{print $1}'`
    if [ $n_unks -gt 30 ]; then
	echo "Skipping sentence. Too much unks ($n_unks)"
    else
	# For each UNK 
	while read  unk_word; do
	    # Compute the alignments
	    python ${ibm1} 1 ${tmp}/src_sent ${src_trg_prefix} ${src_prefix} ${trg_prefix} > ${tmp}/alignments
	    # Get the probability of the alignments
	    cat ${tmp}/alignments | awk '{print $2}' > ${tmp}/alignments_probs
	    echo -n "" > ${tmp}/hypotheses
	    # For each alignment
	    while read alignment; do
		# Generate a new hypothesis (substituting the UNK word by the aligned word)
		align_word=`echo "${alignment}" | awk '{print $1}'` 
		if [ "$align_word" == "/" ]; then
		    align_word="\/"
		fi
		if [ "$align_word" == "\\" ]; then
		    align_word="\\"
		fi
		echo "${edited_sentence}" | sed "0,/UNK/s//${align_word}/"  >> ${tmp}/hypotheses
	    done < ${tmp}/alignments
	    # Compute the LM (log) probability of each hypothesis
	    # echo "${SRILM}/ngram -ppl  ${tmp}/hypotheses  -lm ${lm} -order ${order}  -debug 2 |grep logprob |awk '{print $ 4}' |head -n -1 > ${tmp}/lm_probs"
	    
	    ${SRILM}/ngram -ppl  ${tmp}/hypotheses  -lm ${LM} -order ${order}  -debug 2 2>/dev/null |grep logprob |awk '{print $4}' |head -n -1 > ${tmp}/lm_probs
	    
	    echo -n ""  > ${tmp}/combined_probs
	    # Compute the combined probability of the LM and TM (IBM model)
	    while read -r -u 4 ibm && read -r -u 5 lm ;
	    do
		echo "${lambda}*${ibm} + (1-${lambda})*${lm}" | bc >>  ${tmp}/combined_probs
	    done 4<${tmp}/alignments_probs 5<${tmp}/lm_probs
	    
	    
	    # Set scores to hypotheses
	    echo -n  "" >	${tmp}/hyp_scores
	while read -r -u 4 hypotheses && read -r -u 5 probs ;
	do
	    echo -e "${probs}\t${hypotheses}" >>  ${tmp}/hyp_scores
	done 4<${tmp}/hypotheses 5<${tmp}/combined_probs
	
	# Select the most probable hypothesis
	sort -nr   ${tmp}/hyp_scores > ${tmp}/sorted_hyp
	
	edited_sentence=`head -n 1 ${tmp}/sorted_hyp |awk 'BEGIN {FS="\t"}{print $2}'`
	#echo "Edited sentence: ${edited_sentence}"
	
	if [ $v_given -eq 1 ]; then
	    #echo "Unkown word \"$unk_word\" translated to \"$translation\""
	    echo "Old sentence:"
	    echo "$sentence"
	    echo "Edited sentence: ${edited_sentence}"
	    echo ""
	fi
	done <${tmp}/unk_words
    fi
    rm ${tmp}/unk_words
    echo "${edited_sentence}" >> ${output}
    
done 2<${input} 3<${src_file}
# Remove the <eos> tokens
sed -Ei 's/<eos>//g' ${output}
}


launch_align_NN(){

IFS=''
echo -n "" > $output
echo "Using Thot translations"

while read  sentence; do
    # Extract the words which originated the UNK from the sentence
    echo "${sentence}" | grep  "UNK_\w*" -o |cut -d _ -f 2 > ${tmp}/unk_words
    edited_sentence=`echo ${sentence}` 
    i=`echo ${i}+1 |bc -l`
    echo "Reading sentence ${i}"
    #For each UNK  
    n_unks=`wc -l ${tmp}/unk_words | awk '{print $1}'`
    if [ $n_unks -gt 0 ]; then
	
	while read  unk_word; do	
	    align_word=`${THOT}/thot_client -i 127.0.0.1 -uid 0 -sc "${unk_word}"`
	    
	    if [ $v_given -eq 1 ]; then
		echo "Translating $unk_word into $align_word"
	    fi
	    if [ "$align_word" == "/" ]; then
		align_word="\/"
	    fi
	    if [ "$align_word" == "\\" ]; then
		align_word="\\"
	    fi
	    edited_sentence=`echo "${edited_sentence}" | sed "0,/UNK_\w*/s//${align_word}/"`
	    
	    if [ $v_given -eq 1 ]; then
		#echo "Unkown word \"$unk_word\" translated to \"$translation\""
		echo "Old sentence:"
		echo "$sentence"
		echo "Edited sentence: ${edited_sentence}"
		echo ""
	    fi
	done <${tmp}/unk_words
	rm ${tmp}/unk_words
    else
	if [ $v_given -eq 1 ]; then
	    echo "Sentence with no UNKS"
	fi
    fi
    echo "${edited_sentence}" >> ${output}
done<${input}

# Remove the <eos> tokens
sed -Ei 's/<eos>//g' ${output}
}

input=""
input_given=0
out="" 
debug=0
LM=""
lm_given=0
order="5"
ibm1="/home/alvaro/smt/software/tm_systems_combination/src/get_list_alignments.py"
tmp="./"
lambda="0.5"
v=""
src_file=""
src_trg_prefix=""
src_prefix=""
trg_prefix=""

v_given=0
giza_align=0

if [ $# -eq 0 ]; then
    usage 
    exit 1;
fi

 
while [ $# -ne 0 ]; do
 case $1 in
     "--help") usage
         exit 0
         ;;

     "-h") usage
         exit 0
         ;;


     "-i") shift
         if [ $# -ne 0 ]; then
             input=$1
	     input_given=1
         else
             input=""
	     input_given=0
         fi
         ;;


     "-o") shift
         if [ $# -ne 0 ]; then
             output=$1
	     output_given=1
         else
             output=""
	     output_given=0
         fi
         ;;

     "-giza") shift
         if [ $# -ne 0 ]; then
	     giza_align=1
	     src_file=$1
         else
	     giza_given=0
	     src_file=""
         fi
         ;;

     "-lm") shift
         if [ $# -ne 0 ]; then
             LM=$1
	     lm_given=1
         else
             LM=""
	     lm_given=0
         fi
         ;;

    "-order") shift
         if [ $# -ne 0 ]; then
             order=$1
	 else
             order="5"
	 fi
         ;;


    "-lambda") shift
         if [ $# -ne 0 ]; then
             lambda=$1
	 else
             lambda="0.5"
	 fi
         ;;


    "-tmp") shift
         if [ $# -ne 0 ]; then
             tmp=$1
	 else
             tmp="/tmp"
	 fi
         ;;
    "-ibm1") shift
         if [ $# -ne 0 ]; then
             ibm1=$1
	 else
             ibm1="/home/alvaro/smt/software/tm_systems_combination/src/get_list_alignments.py"
	 fi
         ;;



    "-src_trg") shift
         if [ $# -ne 0 ]; then
             src_trg_prefix=$1
	 else
             src_trg_prefix=""
	 fi
         ;;



    "-trg") shift
         if [ $# -ne 0 ]; then
             trg_prefix=$1
	 else
             trg_prefix=""
	 fi
         ;;


    "-src") shift
         if [ $# -ne 0 ]; then
             src_prefix=$1
	 else
             src_prefix=""
	 fi
         ;;



    "-v") 
         v="--v"
	 v_given=1
	 shift
         ;;

     "-debug") 
         debug=1
	 shift
         ;;
     esac
    shift
done  



#Verify parameters
  
if [ ${input_given} -eq 0 ]; then
    # invalid parameters
    echo "Error: -i option not given"
    exit 1
fi
 
 
if [ ${output_given} -eq 0 ]; then
    # invalid parameters
    echo "Error: -o option not given"
    exit 1
fi

if [ ${lm_given} -eq 0 ]; then
    # invalid parameters
    echo "Error: -lm option not given"
    exit 1
fi



# Parameters are ok. Launch! 


if [ ${v_given} -eq 1 ]; then
    echo "Reading from ${input}"
fi

mkdir -p ${tmp}

if [ ${giza_align} -eq 1 ]; then
    launch_align_GIZA
else
    launch_align_NN
fi





if [ ${v_given} -eq 1 ]; then
    echo "Ende"
fi


if [ ${debug} -eq 0 ]; then
clean
fi
