#/bin/bash 

#$ -l h_rt=4:00:00
#$ -l h_vmem=16g                                                                                                                       
 

export LD_LIBRARY_PATH=/home/lvapeab/smt/software/tcl/lib
srilmpath=/home/lvapeab/smt/software/srilm/bin/i686-m64

task_path=/home/lvapeab/smt/tasks/europarl

for lang in en fr; do
    trainfile=${task_path}/DATA/training.${lang}
    for order in 5;    do
	dest=${task_path}/LM/${order}gram.${lang}
	$srilmpath/ngram-count -text $trainfile -order $order -lm $dest -kndiscount -interpolate -unk   #-gt3min 0 -gt4min 0 -gt5min 0 
    done
done
