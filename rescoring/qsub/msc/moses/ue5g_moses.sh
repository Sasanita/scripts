#!/bin/bash

#$ -l h_rt=140:00:00 
export THEANO_FLAGS=device=cpu,floatX=float32,gcc.cxxflags="-L /usr/lib64"
export PYTHONPATH=/home/lvapeab/smt/software/loopy/loopy/bin:${PYTHONPATH}
export LD_LIBRARY_PATH=/home/lvapeab/lib64:/home/lvapeab/bin:/home/apps/ompi/1.6.4/gnu/lib:/home/apps/oge/lib/linux-x64:/home/lvapeab/lib64:/home/lvapeab/bin:/home/apps/ompi/1.6.4/gnu/lib:/home/apps/oge/lib/linux-x64:/opt/intel/mkl/lib/intel64:/opt/intel/composer_xe_2013/lib/intel64/:/home/lvapeab/smt/software/boost_1_56_0/lib:/usr/lib64:/home/lvapeab/libexec/gcc/x86_64-unknown-linux-gnu/4.9.1/:${LD_LIBRARY_PATH}
export PATH=/home/lvapeab/smt/software/loopy/loopy/bin:/home/lvapeab/bin:/home/apps/oge/bin/linux-x64:${PATH}
export CPATH=/usr/lib64:${CPATH}

#General parameters
rescorer=/home/lvapeab/smt/software/scripts/rescoring/moses/nbl_rescoring_groundhog_moses
test_script=/home/lvapeab/smt/software/scripts/bLM/testModel.sh
reranker=/home/lvapeab/smt/software/scripts/rescoring/moses/qs_rerank.sh
splitter=/home/lvapeab/smt/software/scripts/rescoring/moses/split_nbest.sh

bLM="/home/lvapeab/smt/software/myGroundHog/tutorials/LM/400_620state.pkl"
#bLM="/home/lvapeab/smt/software/myGroundHog/tutorials/LM/miniUE1soft/en_infreq150s_620dstate.pkl"

name="UE5_100v2"
pr="80"
lambda=1


#Task dependant parameters
base_dir=/home/lvapeab/smt/tasks/ue/esen/MOSES/model/
nblist=${base_dir}/test/100best
output=${base_dir}/bidir_result

tdir=/home/lvapeab

weights=/home/lvapeab/smt/tasks/ue/esen/MOSES/model/mert-work/run5.weights.txt
nbest=${tdir}/${name}_rescoring/${name}.nbl
nb_dir=${tdir}/${name}_rescoring/split
output=${tdir}/${name}_rescoring/rescored


mkdir -p $output
mkdir -p $nb_dir
echo "Model: $bLM"
echo "Name: $name"

echo "Processors: $pr"

echo "Base dir: $base_dir"
echo "Temporal dir: $tdir"
echo "N-Best list: $nblist"
echo "Output prefix: $output"
echo "Weights: $weights"
echo "Rescored nbest: $nbest"
echo "Rescoring dir: $nb_dir"
echo "Output dir: $output"


echo "Rescoring nbest list"

$rescorer -tdir $tdir  -bdir $base_dir -pr $pr -qs "-l h_vmem=4g,h_rt=60:00:00" -sdir /home/lvapeab -wgdir $wgdir  -o $output -v -debug -name $name -bLM $bLM -test_script $test_script -nbest $nblist -o $output



echo "Splitting nbest list"
$splitter $nbest $nb_dir/$name
echo "List split"

echo "Resorting list"

$reranker -tdir /home/lvapeab  -nbdir $nb_dir -weights ${weights} -pr $pr -qs "-l h_vmem=4g,h_rt=60:00:00" -sdir /home/lvapeab  -o $output -v -debug -name $name