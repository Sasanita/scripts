"""
Test existing model
"""
class Unbuffered:
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        self.stream.write(data)
        self.stream.flush()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)
import sys
import traceback
sys.stdout = Unbuffered(sys.stdout)
# Generic imports
import numpy
import cPickle
import gzip
import time
import signal
import pprint
import theano
import theano.tensor as TT

from groundhog.utils import print_mem, print_time
from groundhog.layers import MultiLayer, \
       RecurrentMultiLayer, \
       RecurrentMultiLayerInp, \
       RecurrentMultiLayerShortPath, \
       RecurrentMultiLayerShortPathInp, \
       RecurrentMultiLayerShortPathInpAll, \
       SoftmaxLayer, \
       LastState,\
       UnaryOp, \
       DropOp, \
       Operator, \
       Shift, \
       GaussianNoise, \
       SigmoidLayer, \
       Concatenate
from groundhog.layers import maxpool, \
        maxpool_ntimes, \
        last, \
        last_ntimes,\
        tanh, \
        sigmoid, \
        rectifier,\
        hard_sigmoid, \
        hard_tanh



from groundhog.datasets import LMIterator
from groundhog.models import LM_Model

linear = lambda x:x
rect = lambda x:TT.maximum(0., x)

def parse_input(state, word2idx, line, raise_unk=False, idx2word=None, unk_sym=-1,null_sym = -1):
    if unk_sym < 0:
        unk_sym = '<unk>'
    seqin = line.split()
    seqlen = len(seqin)
    seq = numpy.zeros(seqlen+1, dtype='int32')
    for idx,sx in enumerate(seqin):
        seq[idx] = word2idx.get(sx, unk_sym) #coge sx; si no existe, unk_sym
        if seq[idx] == unk_sym and raise_unk:
            raise Exception("Unknown word {}".format(sx))

    #seq[-1] = -1
    if idx2word:
        idx2word[null_sym] = '<eos>'
        idx2word[unk_sym] = '<unk>'
        parsed_in = [idx2word[sx] for sx in seq]
        return seq, " ".join(parsed_in)

    return seq, seqin


class BatchTxtIterator(object):

    def __init__(self, state, txt, indx, batch_size, unk_sym=-1, null_sym = -1):
        self.__dict__.update(locals())
        self.__dict__.pop('self')

    def start(self):
        self.txt_file = open(self.txt)

    def _pack(self, seqs):
        num = len(seqs)
        max_len = max(map(len, seqs))
        x = numpy.zeros((num, max_len), dtype="int32")
        x_mask = numpy.zeros((num, max_len), dtype="float32")
        for i, seq in enumerate(seqs):
            x[i, :len(seq)] = seq
            x_mask[i, :len(seq)] = 1.0
        return x.T, x_mask.T

    def __iter__(self):
        return self

    def next(self):
        seqs = []
        try:
            while len(seqs) < self.batch_size:
                line = next(self.txt_file).strip()
                seq, _ = parse_input(self.state, self.indx, line, unk_sym=self.unk_sym, null_sym=self.null_sym)
                seqs.append(seq)
            return self._pack(seqs)
        except StopIteration:
            if not seqs:
                return False#raise StopIteration()
            return self._pack(seqs)


class MainLoop(object):
    def __init__(self,
                 test_iter,
                 test_data,
                 state,
                 model,
                 validate_postprocess
                 ):

        self.test_data = test_data
        self.test_iter = test_iter
        self.model = model
        self.state = state
        self.validate_postprocess = validate_postprocess
        self.timings = {'step' : 0, 'next_offset' : -1}
        self.step = int(timings['step'])


        self.start_time = time.time()
        self.batch_start_time = time.time()




    def test(self):
        #We only test over the forward + backward layer
        model.best_params = [(x.name, x.get_value()) for x in
                                  model.params]        
        numpy.savez(state['prefix'] + '_best_params',
                    **dict(model.best_params))
        state['best_params_pos'] = self.step
        test_data=None
        if test_iter is not None:
            rvals = model.validate_phrases(test_iter)
        elif test_data is not None :
            rvals = model.validate(test_data)
        else:
            rvals = []
        msg = '>>>         Test'
        pos = self.step // state['validFreq']
        
        for k,v in rvals: 
            msg = msg + ' ' + k + ':%6.3f ' % v
            timings['test' + k][pos] = float(v)
            state['test' + k] = float(v)
        print msg
        state['testtime'] = float(time.time()-self.start_time)/60.

    def main(self):
        print_mem('start') 
        
        #if test_data is not None:
        self.test()
        print 'Took', (time.time() - self.start_time)/60., 'min'
        avg_step = timings['time_step'][:self.step].mean()
        avg_cost2expl = timings['log2_p_expl'][:self.step].mean()
        print "Average step took {}".format(avg_step)
        print "That amounts to {} sentences in a day".format(1 / avg_step * 86400 * state['bs'])
        print "Average log2 per example is {}".format(avg_cost2expl)










def get_text_data(state, path):

    def out_format_test (x, y, r) :
        return {'x':x,'y' :y, 'reset': r}
    test_data = LMIterator(
            batch_size=state['bs'],
            path = path,
            stop=-1,
            use_infinite_loop=False,
            allow_short_sequences=True,
            seq_len= state['seqlen'],
            mode="test",
            chunks=state['chunks'],
            shift = state['shift'],
            output_format = out_format_test,
            can_fit=True
            )
    return test_data
state_path = sys.argv[1]
#data_path = sys.argv[2]
test_path = sys.argv[2]

    #Ojo con no cargar modelos de rigel en local y de local en rigel! Si se hace, hay que cambiar a mano (en el .pkl):
    #El prefix y los datos (diccionario y datos en si)
state = {}
print "State: ",state_path
with open(state_path) as src:
    state.update(cPickle.load(src))

print "State loaded"
state['seqlen'] = 300
rng = numpy.random.RandomState(state['seed'])
print "Loading data..."
test_data = "" #get_text_data(state,data_path) 


#--------------------------------------------------MODEL--------------------------------------------------
### Define Theano Input Variables
x = TT.lvector('x')
y = TT.lvector('y')

h0_f   = theano.shared(numpy.zeros((eval(state['nhids'])[-1],), dtype='float32'))
h0_b   = theano.shared(numpy.zeros((eval(state['nhids'])[-1],), dtype='float32'))
h0 = theano.shared(numpy.zeros((eval(state['nhids'])[-1],), dtype='float32'))


    ### Neural Implementation of the Operators: \oplus                                                                                                                                                               
    #### Word Embedding                                           
emb_words = MultiLayer(
    rng,
    n_in=state['n_in'],
    n_hids=eval(state['inp_nhids']),
    activation=eval(state['inp_activ']),
    init_fn='sample_weights_classic',
    weight_noise=state['weight_noise'],
    rank_n_approx = state['rank_n_approx'],
    scale=state['inp_scale'],
    sparsity=state['inp_sparse'],
    learn_bias = True,
    bias_scale=eval(state['inp_bias']),
    name='emb_words')


    #### Deep Transition Recurrent Layer                                                     
rec_f = eval(state['rec_layer'])(
    rng,
    eval(state['nhids']),
    activation = eval(state['rec_activ']),                                                 
    bias_scale = eval(state['rec_bias']),
    scale=eval(state['rec_scale']),
    sparsity=eval(state['rec_sparse']),
    init_fn=eval(state['rec_init']),
    weight_noise=state['weight_noise'],
    name='rec')


rec_b = eval(state['rec_layer'])(
    rng,
    eval(state['nhids']),
    activation = eval(state['rec_activ']),
    bias_scale = eval(state['rec_bias']),
    scale=eval(state['rec_scale']),
    sparsity=eval(state['rec_sparse']),
    init_fn=eval(state['rec_init']),
    weight_noise=state['weight_noise'],
    name='rec_b')

    #Concatenar las capas:                                                                                                                                                                                           
    #### Stiching them together                                                                                                                                                                                      
    ##### (1) Get the embedding of a word
                               
x_emb = emb_words(x, no_noise_bias=state['no_noise_bias'])
x_emb_b = emb_words(x[::-1], no_noise_bias=state['no_noise_bias'])

    ##### (2) Embedding + Hidden State via DT Recurrent Layer                                                                                                                                                        
reset = TT.scalar('reset')

rec_layer_f = rec_f(x_emb, n_steps=x.shape[0],
                    init_state=h0_f*reset,
                    no_noise_bias=state['no_noise_bias'],
                    truncate_gradient=state['truncate_gradient'],
                    batch_size=1)

rec_layer_b = rec_b(x_emb_b, n_steps=x[::-1].shape[0],
                    init_state=h0_b*reset,
                    no_noise_bias=state['no_noise_bias'],
                    truncate_gradient=state['truncate_gradient'],
                    batch_size=1)


    ## BEGIN Exercise: DOT-RNN                      
    ### Neural Implementation of the Operators: \lhd
    #### Exercise (1)                               
    #### Hidden state -> Intermediate Layer                   

emb_state = MultiLayer(
    rng,
    n_in=eval(state['nhids'])[-1],
    n_hids=eval(state['dout_nhid']),
    activation=linear,
    init_fn=eval(state['dout_init']),
    weight_noise=state['weight_noise'],
    scale=state['dout_scale'],
    sparsity=state['dout_sparse'],
    learn_bias = True,
    bias_scale=eval(state['dout_bias']),
    name='emb_state_f')


emb_state_b = MultiLayer(
    rng,
    n_in=eval(state['nhids'])[-1],
    n_hids=eval(state['dout_nhid']),
    activation=linear,
    init_fn=eval(state['dout_init']),
    weight_noise=state['weight_noise'],
    scale=state['dout_scale'],
    sparsity=state['dout_sparse'],
    learn_bias = True,
    bias_scale=eval(state['dout_bias']),
    name='emb_state_b')


    #### Exercise (1)                                                                                                                                                                                                         
    #### Input -> Intermediate

emb_words_out_f = MultiLayer(
    rng,
    n_in=state['n_in'],
    n_hids=eval(state['dout_nhid']),
    activation=linear,
    init_fn='sample_weights_classic',
    weight_noise=state['weight_noise'],
    scale=state['dout_scale'],
    sparsity=state['dout_sparse'],
    rank_n_approx=state['dout_rank_n_approx'],
    learn_bias = False,
    bias_scale=eval(state['dout_bias']),
    name='emb_words_out')


emb_words_out_b = MultiLayer(
    rng,
    n_in=state['n_in'],
    n_hids=eval(state['dout_nhid']),
    activation=linear,
    init_fn='sample_weights_classic',
    weight_noise=state['weight_noise'],
    scale=state['dout_scale'],
    sparsity=state['dout_sparse'],
    rank_n_approx=state['dout_rank_n_approx'],
    learn_bias = False,
    bias_scale=eval(state['dout_bias']),
    name='emb_words_out_b')


    #### Hidden State: Combine emb_state and emb_words_out 
    #### Exercise (1) 
                                                                                                                                                             
outhid_activ_f = UnaryOp(activation=eval(state['dout_activ']))
outhid_activ_b = UnaryOp(activation=eval(state['dout_activ']))
outhid_activ = UnaryOp(activation=eval(state['dout_activ']))


    #### Exercise (2)                     
outhid_dropout_f = DropOp(dropout=state['dropout'], rng=rng)
outhid_dropout_b = DropOp(dropout=state['dropout'], rng=rng)
outhid_dropout= DropOp(dropout=state['dropout'], rng=rng)


    #### Softmax Layer         
output_layer = SoftmaxLayer(
    rng,
    eval(state['dout_nhid']),
    state['n_out'],
    scale=state['out_scale'],
    bias_scale=state['out_bias_scale'],
    init_fn="sample_weights_classic",
    weight_noise=state['weight_noise'],
    sparsity=state['out_sparse'],
    sum_over_time=False,
    name='out')

    ### Few Optional Things  
    #### Direct shortcut from x to y            

if state['shortcut_inpout']:
    shortcut = MultiLayer(
        rng,
        n_in=state['n_in'],
        n_hids=eval(state['inpout_nhids']),
        activation=eval(state['inpout_activ']),
        init_fn='sample_weights_classic',
        weight_noise = state['weight_noise'],
        scale=eval(state['inpout_scale']),
        sparsity=eval(state['inpout_sparse']),
        learn_bias=eval(state['inpout_learn_bias']),
        bias_scale=eval(state['inpout_bias']),
        name='shortcut')

    shortcut_b = MultiLayer(
        rng,
        n_in=state['n_in'],
        n_hids=eval(state['inpout_nhids']),
        activation=eval(state['inpout_activ']),
        init_fn='sample_weights_classic',
        weight_noise = state['weight_noise'],
        scale=eval(state['inpout_scale']),
        sparsity=eval(state['inpout_sparse']),
        learn_bias=eval(state['inpout_learn_bias']),
        bias_scale=eval(state['inpout_bias']),
        name='shortcut_b')


    #### Learning rate scheduling (1/(1+n/beta))           

state['clr'] = state['lr']


#####################################################################################################################                                                  
####Building train model                                                                           
#####################################################################################################################         
    ### Neural Implementations of the Language Model                             
    #### Training     
                        
if state['shortcut_inpout']:
    additional_inputs = [rec_layer_f, shortcut(x)]
    additional_inputs_b = [rec_layer_b, shortcut(x[::-1])]
else:
    additional_inputs = [rec_layer_f]
    additional_inputs_b = [rec_layer_b]
    
    

    ##### Exercise (1): Compute the output intermediate layer       
outhid = outhid_activ(emb_state(rec_layer_f) + emb_words_out_f(x)+ emb_state_b(rec_layer_b) + emb_words_out_b(x)) 
    ##### Exercise (2): Apply Dropout                               
outhid = outhid_dropout(outhid)


train_model = output_layer(outhid,
                           no_noise_bias=state['no_noise_bias'],
                           additional_inputs=additional_inputs).train(target=y,
                                                                      scale=numpy.float32(1./1))#state['seqlen']))


nw_h0_f = rec_layer_f.out[rec_layer_f.out.shape[0]-1]
nw_h0_b = rec_layer_b.out[rec_layer_b.out.shape[0]-1]     
nw_h0 = nw_h0_f + nw_h0_b




h0val_f = theano.shared(numpy.zeros((eval(state['nhids'])[-1],), dtype='float32'))
rec_layer_f = rec_f(emb_words(x, use_noise=False),
                    n_steps = x.shape[0],
                    batch_size=1,
                    init_state=h0val_f*reset,
                    use_noise=False)

h0val_b = theano.shared(numpy.zeros((eval(state['nhids'])[-1],), dtype='float32'))
rec_layer_b = rec_b(emb_words(x[::-1], use_noise=False),
                    n_steps = x[::-1].shape[0],
                    batch_size=1,
                    init_state=h0val_b*reset,
                    use_noise=False)

h0val = theano.shared(numpy.zeros((eval(state['nhids'])[-1],), dtype='float32'))                                    

nw_h0_f = rec_layer_f.out[rec_layer_f.out.shape[0]-1]
nw_h0_b = rec_layer_b.out[rec_layer_b.out.shape[0]-1]
nw_h0 = nw_h0_f + nw_h0_b


valid_model = output_layer(outhid,
                           additional_inputs=additional_inputs,
                           use_noise=False).validate(target=y, sum_over_time=True)

valid_fn = theano.function([x, y, reset], valid_model.cost,
                           name='valid_fn',   updates=[], #No updates
                           on_unused_input='warn'
                           )



model_path = state['prefix'] + 'model.npz'
timings_path = state['prefix'] + 'timing.npz'

try:
    print "Loading model" 
    model = LM_Model(
        cost_layer = train_model,
        weight_noise_amount=state['weight_noise_amount'],
        valid_fn =  valid_fn,
        clean_before_noise_fn = False,
        noise_fn = None,
        test_verbosity = 0,
        cost_per_sample=True,
        indx_word=state['dictionary'],
        rng = rng)
    model.load(model_path)
    print "Model loaded"
except Exception:
    print 'mainLoop: Corrupted model file'
    traceback.print_exc()
try:
    timings = dict(numpy.load(timings_path).iteritems())
except Exception:
    print 'mainLoop: Corrupted timings file'
    traceback.print_exc()

data_model = numpy.load(state['path'])
indx = data_model['vocabulary'].item()


test_iter = BatchTxtIterator(state,     # LM state
                                  test_path,# Text to parse
                                  indx,  # Dictionary word2index
                                  batch_size = state['bs'],
                                  unk_sym=indx['<unk>'], 
                                  null_sym=None
                                  )   


print "Testing..."

main = MainLoop(  test_iter,
                  test_data,
                  state,
                  model,
                  validate_postprocess =  eval(state['validate_postprocess'])
                  )
    ## Run!
main.main()
