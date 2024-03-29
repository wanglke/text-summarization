import tensorflow as tf
import argparse
import pickle
import os
from model import Model
from utils import build_dict,build_dataset,batch_iter

# =======================start setting args====================
def add_arguments(parser):
    """
    参数设置
    :param parser:
    :return:
    """
    parser.add_argument("--num_hidden",type=int,default=96,help="Network size.")
    parser.add_argument("--num_layers",type=int,default=2,help="Network depth.")
    parser.add_argument("--beam_width",type=int,default=10,help="eam width for beam search decoder.")
    parser.add_argument("--glove",action="store_true", help="Use glove as initial word embedding.")
    parser.add_argument("--embedding_size", type=int, default=100, help="Word embedding size.")

    parser.add_argument("--learning_rate", type=float, default=0.0005, help="Learning rate.")
    parser.add_argument("--batch_size", type=int, default=256, help="Batch size.")
    parser.add_argument("--num_epochs", type=int, default=100, help="Number of epochs.")
    parser.add_argument("--keep_prob", type=float, default=0.8, help="Dropout keep prob.")

    parser.add_argument("--toy", action="store_true",default=False, help="Use only 50K samples of data")

parser=argparse.ArgumentParser()
add_arguments(parser)
args=parser.parse_args()
with open("result/args.pickle","wb") as out_data:
    pickle.dump(args,out_data)
# =======================end setting args====================


# =======================start preparing data================
if not os.path.exists("result/saved_model"):
    os.mkdir("result/saved_model")

print("building dictionary....")
word_dict,reversed_dict,article_max_len,summary_max_len=build_dict("train",args.toy)
print("loading training dataset..")
train_x,train_y=build_dataset("train",word_dict,article_max_len,summary_max_len,args.toy)
# =======================end preparing data================

# ======================= start training===================
with tf.Session() as sess:
    model=Model(reversed_dict,article_max_len,summary_max_len,args)
    sess.run(tf.global_variables_initializer())
    saver=tf.train.Saver(tf.global_variables())

    batches=batch_iter(train_x,train_y,args.batch_size,args.num_epochs)
    num_batches_per_epoch=(len(train_x)-1)//args.batch_size+1 # 每轮batch的数量

    print("Iteration starts.")
    print("Number of batches per epoch:",num_batches_per_epoch)

    for batch_x,batch_y in batches:
        batch_x_len=list(map(lambda x:len([y for y in x if y!=0]),batch_x))
        batch_decoder_input=list(map(lambda x:[word_dict["<s>"]]+list(x),batch_y))
        batch_decoder_len=list(map(lambda x:len([y for y in x if y!=0]),batch_decoder_input))
        batch_decoder_output=list(map(lambda x:list(x)+[word_dict["</s>"]],batch_y))

        batch_decoder_input=list(
            map(lambda d:d+(summary_max_len-len(d))*[word_dict["<padding>"]],batch_decoder_input)
        )
        batch_decoder_output = list(
            map(lambda d:d+(summary_max_len - len(d)) * [word_dict["<padding>"]], batch_decoder_output)
        )

        train_feed_dict={
            model.batch_size:len(batch_x),
            model.X:batch_x,
            model.X_len:batch_x_len,
            model.decoder_input:batch_decoder_input,
            model.decoder_len:batch_decoder_len,
            model.decoder_target:batch_decoder_output
        }

        _,step,loss=sess.run([model.update, model.global_step, model.loss],feed_dict=train_feed_dict)

        if step % 100==0:
            print("step {0}:loss={1}".format(step,loss))

        if step%(num_batches_per_epoch*5)==0:
          saver.save(sess,"result/saved_model/model.ckpt",global_step=step)
          print("Epoch {0}:Model is saved.".format(step//num_batches_per_epoch))