from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import boto3
import subprocess
import numpy as np
import tensorflow as tf
# import keras

import argparse
import os
import re
import sys
import urllib
import json

SESSION = None

def downloadFromS3(strBucket,strKey,strFile):
    s3_client = boto3.client('s3')
    s3_client.download_file(strBucket, strKey, strFile)

class NodeLookup(object):
    """Converts integer node ID's to human readable labels."""

    def __init__(self,
               label_lookup_path=None,
               uid_lookup_path=None):
        if not label_lookup_path:
            label_lookup_path = os.path.join(
                '/var/task/', 'imagenet_2012_challenge_label_map_proto.pbtxt')
        if not uid_lookup_path:
            uid_lookup_path = os.path.join(
                '/var/task/', 'imagenet_synset_to_human_label_map.txt')
        self.node_lookup = self.load(label_lookup_path, uid_lookup_path)

    def load(self, label_lookup_path, uid_lookup_path):
        if not tf.gfile.Exists(uid_lookup_path):
            tf.logging.fatal('File does not exist %s', uid_lookup_path)
        if not tf.gfile.Exists(label_lookup_path):
            tf.logging.fatal('File does not exist %s', label_lookup_path)

        # Loads mapping from string UID to human-readable string
        proto_as_ascii_lines = tf.gfile.GFile(uid_lookup_path).readlines()
        uid_to_human = {}
        p = re.compile(r'[n\d]*[ \S,]*')
        for line in proto_as_ascii_lines:
            parsed_items = p.findall(line)
            uid = parsed_items[0]
            human_string = parsed_items[2]
            uid_to_human[uid] = human_string

        # Loads mapping from string UID to integer node ID.
        node_id_to_uid = {}
        proto_as_ascii = tf.gfile.GFile(label_lookup_path).readlines()
        for line in proto_as_ascii:
            if line.startswith('  target_class:'):
                target_class = int(line.split(': ')[1])
            if line.startswith('  target_class_string:'):
                target_class_string = line.split(': ')[1]
                node_id_to_uid[target_class] = target_class_string[1:-2]

        # Loads the final mapping of integer node ID to human-readable string
        node_id_to_name = {}
        for key, val in node_id_to_uid.items():
            if val not in uid_to_human:
                tf.logging.fatal('Failed to locate: %s', val)
            name = uid_to_human[val]
            node_id_to_name[key] = name

        return node_id_to_name

    def id_to_string(self, node_id):
        if node_id not in self.node_lookup:
            return ''
        return self.node_lookup[node_id]


def create_graph():
    with tf.gfile.FastGFile(os.path.join('/var/task/', 'classify_image_graph_def.pb'), 'rb') as f:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(f.read())
        _ = tf.import_graph_def(graph_def, name='')

def run_inference_on_image(image):
    global SESSION
    if not tf.gfile.Exists(image):
        tf.logging.fatal('File does not exist %s', image)
    image_data = tf.gfile.FastGFile(image, 'rb').read()

  # Creates graph from saved GraphDef.
    # create_graph()
    if SESSION is None:
        SESSION = tf.InteractiveSession()
        create_graph()

    # with tf.Session() as sess:
        # Some useful tensors:
        # 'softmax:0': A tensor containing the normalized prediction across
        #   1000 labels.
        # 'pool_3:0': A tensor containing the next-to-last layer containing 2048
        #   float description of the image.
        # 'DecodeJpeg/contents:0': A tensor containing a string providing JPEG
        #   encoding of the image.
        # Runs the softmax tensor by feeding the image_data as input to the graph.
    softmax_tensor = tf.get_default_graph().get_tensor_by_name('softmax:0')
    predictions = SESSION.run(softmax_tensor,
                           {'DecodeJpeg/contents:0': image_data})
    predictions = np.squeeze(predictions)

    # Creates node ID --> English string lookup.
    node_lookup = NodeLookup()

    top_k = predictions.argsort()[-5:][::-1]
    strResult = '%s (score = %.5f)' % (node_lookup.id_to_string(top_k[0]), predictions[top_k[0]])
    strResultExtended = []
    for node_id in top_k:
        human_string = node_lookup.id_to_string(node_id)
        score = predictions[node_id]
        print('%s (score = %.5f)' % (human_string, score))
        strResultExtended.append({ "label": human_string, "probability": "{:.9f}".format(score)}) # round(score, 5)
        #strResultExtended.append('{ "label": %s, "probability": %.5f }' % (human_string, score))
    return strResultExtended

def handler(event, context):
    print(event)
    # print(event["body"])

    # Spielwiese ---------
    #if(event["queryStringParameters"]['image'] == 'fabian'):
    #    print(event["queryStringParameters"]['image'])
    #else:
    #    print('Event API Error')
    # Ende Spielwiese ----

    print(context)
    if not os.path.exists('/tmp/'):
        os.makedirs('/tmp/')

    # ryfeuslambda
    #print('Loading models from S3: ieee-tensorflow')
    #strBucket = 'ieee-tensorflow'
    #strKey = 'tensorflow/imagenet/imagenet_synset_to_human_label_map.txt'
    #strFile = '/tmp/imagenet/imagenet_synset_to_human_label_map.txt'
    #downloadFromS3(strBucket,strKey,strFile)  
    #print(strFile)

    #strBucket = 'ieee-tensorflow'
    #strKey = 'tensorflow/imagenet/imagenet_2012_challenge_label_map_proto.pbtxt'
    #strFile = '/tmp/imagenet/imagenet_2012_challenge_label_map_proto.pbtxt'
    #downloadFromS3(strBucket,strKey,strFile)
    #print(strFile) 

    #strBucket = 'ieee-tensorflow'
    #strKey = 'tensorflow/imagenet/classify_image_graph_def.pb'
    #strFile = '/tmp/imagenet/classify_image_graph_def.pb'
    #downloadFromS3(strBucket,strKey,strFile)
    #print(strFile)

    strFile = '/tmp/inputimage.jpg'
    if ('imagelink' in event):
        urllib.urlretrieve(event['imagelink'], strFile)
    else:
        strBucket = 'ieeedhbwbucket-karl'
        strKey = ('%s.%s' % (event["queryStringParameters"]['img'], 'jpg'))
        downloadFromS3(strBucket,strKey,strFile)
        print(strFile)

    parser = argparse.ArgumentParser()
    # classify_image_graph_def.pb:
    #   Binary representation of the GraphDef protocol buffer.
    # imagenet_synset_to_human_label_map.txt:
    #   Map from synset ID to a human readable string.
    # imagenet_2012_challenge_label_map_proto.pbtxt:
    #   Text representation of a protocol buffer mapping a label to synset ID.
    parser.add_argument(
      '--model_dir',
      type=str,
      default='/var/task',
      help="""\
      Path to classify_image_graph_def.pb,
      imagenet_synset_to_human_label_map.txt, and
      imagenet_2012_challenge_label_map_proto.pbtxt.\
      """
    )
    parser.add_argument(
      '--image_file',
      type=str,
      default='',
      help='Absolute path to image file.'
    )
    parser.add_argument(
      '--num_top_predictions',
      type=int,
      default=5,
      help='Display this many predictions.'
    )
    FLAGS, unparsed = parser.parse_known_args()
    image = os.path.join('/tmp/', 'inputimage.jpg')
    strResult = run_inference_on_image(image)

    objRet =  {
        'statusCode': 200,
        # 'body': json.dumps({ "predictions": strResult, "prediction": True , "recievedFile": event["body"]})
        'body': json.dumps({ "predictions": strResult, "prediction": True })
    }    
    return objRet