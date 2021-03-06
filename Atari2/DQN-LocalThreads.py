# While training is taking place, statistics on agent performance are available from Tensorboard. To launch it use:
# 
#   tensorboard --logdir=worker_0:'./train_0',worker_1:'./train_1',worker_2:'./train_2',worker_3:'./train_3'
#   tensorboard --logdir=worker_0:'./train_0'
#   tensorboard --logdir=worker_0:'./train_0',worker_1:'./train_1',worker_2:'./train_2',worker_3:'./train_3',worker_4:'./train_4',worker_5:'./train_5',worker_6:'./train_6',worker_7:'./train_7',worker_8:'./train_8',worker_9:'./train_9',worker_10:'./train_10',worker_11:'./train_11'


import argparse
import os
import threading
from time import sleep
#import matplotlib.pyplot as mpl
import gym

from Atari2.atari_environment import AtariEnvironment
#from Atari2.envs import create_atari_env
import tensorflow as tf
from Atari2.QNetwork1step import QNetwork1Step
from Atari2.DQNSlave import Worker


max_episode_length = 10000

gamma = 0.99            # discount rate for advantage estimation and reward discounting
a_size = 3              # Agent can move Left, Right, up down
s_size = [84, 84, 4]
learning_rate = 1e-4    #
load_model = False
model_path = './model'

max_steps = 5000000
exploration_anealing_steps = max_steps * 0.75

parser = argparse.ArgumentParser()
parser.register("type", "bool", lambda v: v.lower() == "true")
parser.add_argument(
    "--num_slaves",
    type=int,
    default=1,
    help="Set number of available CPU threads"
)
FLAGS, unparsed = parser.parse_known_args()

tf.reset_default_graph()

# Create a directory to save models and episode playback gifs
if not os.path.exists(model_path):
    os.makedirs(model_path)
if not os.path.exists('./frames'):
    os.makedirs('./frames')

with tf.device("/cpu:0"):
    global_episodes = tf.Variable(0, dtype=tf.int32, name='global_episodes', trainable=False)
    trainer = tf.train.AdamOptimizer(learning_rate=learning_rate)
    master_network = QNetwork1Step(s_size, a_size, 'global', None)  # Generate global network

    # Create worker classes
    workers = []
    for i in range(FLAGS.num_slaves):
        workers.append(Worker(AtariEnvironment(gym.make("Breakout-v0"), s_size[0], s_size[1], s_size[2]),
                              i, s_size, a_size, trainer, model_path, global_episodes))
    saver = tf.train.Saver()

with tf.Session() as sess:
    coord = tf.train.Coordinator()
    if load_model:
        print('Loading Model...')
        ckpt = tf.train.get_checkpoint_state(model_path)
        saver.restore(sess, ckpt.model_checkpoint_path)
    else:
        sess.run(tf.global_variables_initializer())

    # This is where the asynchronous magic happens.
    # Start the "work" process for each worker in a separate threat.
    worker_threads = []
    for worker in workers:
        worker_work = lambda: worker.work(max_steps, exploration_anealing_steps,
                                          max_episode_length, gamma, sess, coord, saver)
        t = threading.Thread(target=(worker_work))
        t.start()
        sleep(0.5)

        worker_threads.append(t)

    coord.join(worker_threads)

print("Done")
