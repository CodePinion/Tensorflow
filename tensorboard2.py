import tensorflow as tf
import matplotlib.pyplot as plt
import io
import numpy as np
import tensorflow_datasets as tfds

from tensorflow import keras
from tensorflow.keras import layers

# Load cifar10 from tensorflow_datasets
(ds_train, ds_test), ds_info = tfds.load(
    "cifar10",
    split=["train", "test"],
    shuffle_files=True,
    as_supervised=True,
    with_info=True,
)

# Nomalize function
def normalize_img(image, label):
    return tf.cast(image, tf.float32) / 255.0, label

# Augmentation function
def augment(image, label):
    
    if tf.random.uniform((), minval=0, maxval=1) < 0.1:
        image = tf.tile(tf.image.rgb_to_grayscale(image), [1, 1, 3])

    image = tf.image.random_flip_left_right(image)
    image = tf.image.random_brightness(image, max_delta=0.1)

    return image, label

AUTOTUNE = tf.data.experimental.AUTOTUNE
BATCH_SIZE = 32

# Train dataset
ds_train = ds_train.map(normalize_img, num_parallel_calls=AUTOTUNE)
ds_train = ds_train.cache()
ds_train = ds_train.shuffle(ds_info.splits["train"].num_examples)
ds_train = ds_train.map(augment)
ds_train = ds_train.batch(BATCH_SIZE)
ds_train = ds_train.prefetch(AUTOTUNE)

# Test dataset
ds_test = ds_test.map(normalize_img, num_parallel_calls=AUTOTUNE)
ds_test = ds_test.batch(BATCH_SIZE)
ds_test = ds_test.prefetch(AUTOTUNE)


class_name = [
    "airplane",
    "automobile",
    "bird",
    "cat",
    "deer",
    "dog",
    "frog",
    "horse",
    "ship",
    "truck",
]

# Create model function
def get_model():
    model = keras.Sequential(
        [
            layers.Input(shape=(32, 32, 3)),
            layers.Conv2D(8, 3, padding="same", activation="relu"),
            layers.Conv2D(16, 3, padding="same", activation="relu"),
            layers.MaxPooling2D((2, 2)),
            layers.Flatten(),
            layers.Dense(64, activation="relu"),
            layers.Dropout(0.1),
            layers.Dense(10),
        ]
    )
    return model


model = get_model()
num_epoch = 3
loss_fn = keras.losses.SparseCategoricalCrossentropy(from_logits=True)
optimizer = keras.optimizers.Adam(learning_rate=0.001)
acc_metric = keras.metrics.SparseCategoricalAccuracy()
train_writer = tf.summary.create_file_writer("logs/train")
test_writer = tf.summary.create_file_writer("logs/test")
train_step = test_step = 0

for learning_rate in [1e-2, 1e-3, 1e-4, 1e-5]:
    train_step = test_step = 0
    train_writer = tf.summary.create_file_writer("logs/train/" + str(learning_rate))
    test_writer = tf.summary.create_file_writer("logs/test/" + str(learning_rate))
    model = get_model()
    optimizer = keras.optimizers.Adam(learning_rate=learning_rate)

    for epoch in range(num_epoch):
        # Iterate through training set
        for batch_idx, (x, y) in enumerate(ds_train):
            with tf.GradientTape() as tape:
                y_pred = model(x, training=True)
                loss = loss_fn(y, y_pred)

            gradients = tape.gradient(loss, model.trainable_weights)
            optimizer.apply_gradients(zip(gradients, model.trainable_weights))
            acc_metric.update_state(y, y_pred)

            with train_writer.as_default():
                tf.summary.scalar("loss", loss, step=train_step)
                tf.summary.scalar("accuracy", acc_metric.result(), step=train_step)
                train_step += 1

        # reset the accuracy for each epoch
        acc_metric.reset_states()

        # Iterate through test set
        for batch_idx, (x, y) in enumerate(ds_test):
            y_pred = model(x, training=False)
            loss = loss_fn(y, y_pred)
            acc_metric.update_state(y, y_pred)

            with test_writer.as_default():
                tf.summary.scalar("loss", loss, step=test_step)
                tf.summary.scalar("accuracy", acc_metric.result(), step=test_step)    
                test_step += 1

        acc_metric.reset_states()