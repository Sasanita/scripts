#!/bin/bash

tok_path=/home/lvapeab/smt/software/mosesdecoder/scripts/tokenizer
if [ $# -lt 1 ] 
then 
    echo "Usage: $0 language input_file output_file"
    echo "Computes the vocabulary size of text_file"
    exit 1
fi

language=$1
input=$2
output=$3

tmp_name=`basename $output`
echo "Converting to UTF-8"
iconv -t UTF-8 $input > /tmp/${tmp_name}
echo "Removing non printing chars"
${tok_path}/remove-non-printing-char.perl <  /tmp/${tmp_name} > /tmp/${tmp_name}_0
echo "Replacing unicode punctuation"
${tok_path}/replace-unicode-punctuation.perl < /tmp/${tmp_name}_0 > /tmp/${tmp_name}_2
echo "Tokenizing"
${tok_path}/tokenizer.perl -threads 8 -l $language < /tmp/${tmp_name}_2 > ${output}
echo "Done"
rm /tmp/${tmp_name}*
 
