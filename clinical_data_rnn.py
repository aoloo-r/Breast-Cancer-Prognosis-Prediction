# -*- coding: utf-8 -*-
"""Clinical_Data_RNN.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1V_r-EKtPp_mEE1dkrSyG0JSMvMeluFl2

<a href="https://colab.research.google.com/github/alexander-harmaty/Breast-Cancer-Prognosis-Prediction/blob/main/Clinical_Data_RNN.ipynb" target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>

# **Environment Setup and Imports**
"""

# Commented out IPython magic to ensure Python compatibility.
import torch
import re
import torch.nn as nn
import torch.optim as optim
import tensorflow as tf
from tensorflow import keras
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import SimpleRNN, LSTM, GRU, Dense, Dropout
from tensorflow.keras.optimizers import Adam
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc
from tensorflow.keras.layers import Concatenate, BatchNormalization, Input, Bidirectional
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.regularizers import l1_l2
from tensorflow.keras.models import Sequential, Model
from sklearn.metrics import classification_report, confusion_matrix, roc_curve, auc, precision_recall_curve

# Clone repository and set working directory
!git clone https://github.com/alexander-harmaty/Breast-Cancer-Prognosis-Prediction.git
# %cd Breast-Cancer-Prognosis-Prediction

# load the dataset from the repo root
file_path = './Clinical_and_Other_Features.xlsx'
clinical_df = pd.read_excel(file_path, header=[1,2])

"""# **Data Preprocessing**

## *Data Loading and Header Processing*

### utilities
"""

# Function to merge multi-index headers to single index headers
def merge_headers(col_tuple):
    # Unpack the tuple: first-level and second-level names
    first, second = col_tuple

    # If newline characters exist, remove and replace with space
    if isinstance(first, str):
        first = first.replace('\n', ' ').strip()
    if isinstance(second, str):
        second = second.replace('\n', ' ').strip()

    # If blank second-headers exist, return first-header only
    if not second or 'Unnamed' in second:
        return first
    # Otherwise, return merged header
    else:
        return f"{first} - {second}"

"""### scripts"""

# Load the data
file_path = './Clinical_and_Other_Features.xlsx'
clinical_df = pd.read_excel(file_path, header=[1, 2])

# Preprocess the column headers
# Merge multi-index headers for all columns
new_columns = [merge_headers(col) for col in clinical_df.columns]
clinical_df.columns = new_columns

# Print column info
print(f"Total columns: {len(clinical_df.columns)}")
print(f"Sample size: {len(clinical_df)}")

"""## *Data Encoding*

### utilities
"""

def encode_clinical_data(df):
    """
    Encodes clinical data with the understanding that real data starts at row 4.
    Rows 1-3 contain header/metadata information.

    Parameters:
    -----------
    df : pandas.DataFrame
        The clinical dataframe to encode

    Returns:
    --------
    pandas.DataFrame
        The encoded dataframe with all columns properly processed
    """
    # Create a copy to avoid modifying the original
    encoded_df = df.copy()

    # First, check if we need to handle the header rows
    # If the dataframe has already been loaded with headers processed
    # (i.e., headers are in column names), we don't need this step
    if encoded_df.shape[0] >= 4:
        print("Checking if data starts at row 4...")
        # Sample some values to see if first 3 rows appear to be headers
        sample_col = encoded_df.columns[0]
        first_rows = encoded_df.loc[0:3, sample_col].tolist()
        print(f"First rows of sample column: {first_rows}")

        # If first rows look like headers, remove them
        if any(isinstance(val, str) and '=' in str(val) for val in first_rows):
            print("First rows appear to contain metadata. Removing rows 0-3...")
            encoded_df = encoded_df.iloc[3:].reset_index(drop=True)
            print(f"Dataframe shape after removing header rows: {encoded_df.shape}")

    # Identify the target column
    target_col = None
    for col in encoded_df.columns:
        if "Recurrence event" in col:
            target_col = col
            target_values = encoded_df[target_col].copy()
            print(f"Identified target column: {target_col}")
            break

    # Process each column individually
    all_columns = encoded_df.columns.tolist()
    print(f"Processing {len(all_columns)} total columns")

    for col in all_columns:
        # Skip target column for now
        if col == target_col:
            continue

        print(f"Processing column: {col}")

        try:
            # Check column data type
            if encoded_df[col].dtype == 'object':
                # Categorical column
                print(f"  Processing as categorical")

                # Fill missing values
                encoded_df[col] = encoded_df[col].fillna("MISSING")

                # Convert to string
                encoded_df[col] = encoded_df[col].astype(str)

                # Apply label encoding
                le = LabelEncoder()
                encoded_df[col] = le.fit_transform(encoded_df[col])
                print(f"  Encoded {len(le.classes_)} unique values")

            else:
                # Numeric column
                print(f"  Processing as numeric")

                # Handle missing values
                if encoded_df[col].isna().any():
                    if encoded_df[col].isna().all():
                        encoded_df[col] = 0
                        print(f"  All values missing, filled with 0")
                    else:
                        median = encoded_df[col].median()
                        encoded_df[col] = encoded_df[col].fillna(median)
                        print(f"  Filled missing values with median: {median}")

                # Standardize if there's variance
                if encoded_df[col].std() > 0:
                    mean_val = encoded_df[col].mean()
                    std_val = encoded_df[col].std()
                    encoded_df[col] = (encoded_df[col] - mean_val) / std_val
                    print(f"  Standardized numeric column")

        except Exception as e:
            print(f"Error processing column {col}: {str(e)}")

            # Try alternative approach
            try:
                print(f"  Trying alternative encoding approach")

                # Force to string and encode
                encoded_df[col] = encoded_df[col].fillna("MISSING")
                encoded_df[col] = encoded_df[col].astype(str)
                le = LabelEncoder()
                encoded_df[col] = le.fit_transform(encoded_df[col])
                print(f"  Alternative encoding successful")

            except Exception as e2:
                print(f"  Alternative approach failed: {str(e2)}")
                print(f"  Setting column to 0")
                encoded_df[col] = 0

    # Restore target column
    if target_col and 'target_values' in locals():
        encoded_df[target_col] = target_values
        print(f"Restored target column: {target_col}")

    # Final check for any NaN values
    if encoded_df.isna().any().any():
        nan_cols = encoded_df.columns[encoded_df.isna().any()].tolist()
        print(f"Filling NaN values in {len(nan_cols)} columns")
        encoded_df = encoded_df.fillna(0)

    print(f"Final encoded dataframe shape: {encoded_df.shape}")
    return encoded_df

"""### scripts"""

# target variable
target_col = "Recurrence event(s) - {0 = no, 1 = yes}"
if target_col not in clinical_df.columns:
    # Find the correct column name by looking for a substring match
    matching_cols = [col for col in clinical_df.columns if "Recurrence event" in col]
    if matching_cols:
        target_col = matching_cols[0]
        print(f"Found target column: {target_col}")
    else:
        raise ValueError("Target column not found! Please check the column names.")

# Encode the data
encoded_df = encode_clinical_data(clinical_df)
print(f"Encoded data shape: {encoded_df.shape}")

"""## *Data Spliitting and Reshaping*

### utilities
"""



"""### scripts"""

# Split the data into features and target
X = encoded_df.drop(columns=[target_col]) if target_col in encoded_df.columns else encoded_df
y = encoded_df[target_col] if target_col in encoded_df.columns else None

# Print info about target distribution
if y is not None:
    print(f"Target distribution:\n{y.value_counts()}")
else:
    print("Warning: Target column not found in encoded dataframe!")

# Split data into train, validation, and test sets
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.30, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.50, random_state=42)

print("Training set size:", X_train.shape, y_train.shape)
print("Validation set size:", X_val.shape, y_val.shape)
print("Test set size:", X_test.shape, y_test.shape)

# Reshape data for RNN (sequence data)
# RNNs expect input of shape (batch_size, time_steps, features)
X_train_seq = np.expand_dims(X_train.values, axis=1)  # shape: (samples, 1, features)
X_val_seq = np.expand_dims(X_val.values, axis=1)
X_test_seq = np.expand_dims(X_test.values, axis=1)


# Check for NaN values using np.isnan for NumPy arrays
if np.isnan(X_test_seq).any():
    print("Warning: NaN values found in test data! Filling with 0...")
    X_test_seq = np.nan_to_num(X_test_seq, nan=0.0)

X_train_seq = np.nan_to_num(X_train_seq, nan=0.0)
X_val_seq = np.nan_to_num(X_val_seq, nan=0.0)

print("Sequence shapes:")
print("X_train_seq:", X_train_seq.shape)
print("X_val_seq:", X_val_seq.shape)
print("X_test_seq:", X_test_seq.shape)

"""# **RNN Model**

## *Model Building*

### utilities
"""

def build_advanced_rnn_model(input_shape, rnn_type='LSTM', units=64,
                            bidirectional=True, attention=False,
                            dropout_rate=0.3, l1_reg=0.0001, l2_reg=0.0001):
    """
    Build an advanced RNN model with various architectural improvements:
    - Bidirectional RNN layers
    - Batch normalization
    - Regularization (dropout, L1, L2)

    Parameters:
    -----------
    input_shape : tuple
        Shape of input data (time_steps, features)
    rnn_type : str, default='LSTM'
        Type of RNN layer ('LSTM' or 'GRU')
    units : int, default=64
        Number of RNN units
    bidirectional : bool, default=True
        Whether to use bidirectional RNNs
    attention : bool, default=False
        Whether to add an attention mechanism (simplified)
    dropout_rate : float, default=0.3
        Dropout rate for regularization
    l1_reg : float, default=0.0001
        L1 regularization strength
    l2_reg : float, default=0.0001
        L2 regularization strength

    Returns:
    --------
    keras.Model
        Compiled RNN model
    """
    # Simple version for simpler architectural choices
    if not bidirectional:
        model = Sequential()

        # Use specified RNN type
        if rnn_type == 'LSTM':
            model.add(LSTM(units, input_shape=input_shape,
                          kernel_regularizer=l1_l2(l1=l1_reg, l2=l2_reg),
                          recurrent_regularizer=l1_l2(l1=l1_reg, l2=l2_reg),
                          return_sequences=False))
        elif rnn_type == 'GRU':
            model.add(GRU(units, input_shape=input_shape,
                         kernel_regularizer=l1_l2(l1=l1_reg, l2=l2_reg),
                         recurrent_regularizer=l1_l2(l1=l1_reg, l2=l2_reg),
                         return_sequences=False))
        else:
            raise ValueError(f"Unknown RNN type: {rnn_type}")

        model.add(BatchNormalization())
        model.add(Dropout(dropout_rate))
        model.add(Dense(32, activation='relu', kernel_regularizer=l1_l2(l1=l1_reg, l2=l2_reg)))
        model.add(BatchNormalization())
        model.add(Dropout(dropout_rate))
        model.add(Dense(1, activation='sigmoid'))

    # More complex model with bidirectional RNNs
    else:
        # Create functional API model for more flexibility
        inputs = Input(shape=input_shape)

        # Configure RNN layer based on parameters
        if rnn_type == 'LSTM':
            rnn_layer = LSTM(units,
                            kernel_regularizer=l1_l2(l1=l1_reg, l2=l2_reg),
                            recurrent_regularizer=l1_l2(l1=l1_reg, l2=l2_reg),
                            return_sequences=False)  # No need for sequences in this implementation
        elif rnn_type == 'GRU':
            rnn_layer = GRU(units,
                           kernel_regularizer=l1_l2(l1=l1_reg, l2=l2_reg),
                           recurrent_regularizer=l1_l2(l1=l1_reg, l2=l2_reg),
                           return_sequences=False)  # No need for sequences in this implementation
        else:
            raise ValueError(f"Unknown RNN type: {rnn_type}")

        # Add bidirectional wrapper
        rnn_output = Bidirectional(rnn_layer)(inputs)

        # Add dense layers with regularization
        x = BatchNormalization()(rnn_output)
        x = Dropout(dropout_rate)(x)
        x = Dense(32, activation='relu', kernel_regularizer=l1_l2(l1=l1_reg, l2=l2_reg))(x)
        x = BatchNormalization()(x)
        x = Dropout(dropout_rate)(x)
        outputs = Dense(1, activation='sigmoid')(x)

        model = Model(inputs=inputs, outputs=outputs)

    # Compile model
    model.compile(
        optimizer=Adam(learning_rate=0.001),
        loss='binary_crossentropy',
        metrics=['accuracy', tf.keras.metrics.AUC(), tf.keras.metrics.Precision(), tf.keras.metrics.Recall()]
    )

    return model

"""### scripts"""

# Build the advanced RNN model
input_shape = (X_train_seq.shape[1], X_train_seq.shape[2])  # (time_steps, features)
advanced_model = build_advanced_rnn_model(
    input_shape=input_shape,
    rnn_type='LSTM',       # 'LSTM' or 'GRU'
    units=128,             # Number of RNN units
    bidirectional=True,    # Use bidirectional RNN
    attention=False,       # Attention mechanism not needed for this data
    dropout_rate=0.3,      # Dropout rate for regularization
    l1_reg=0.0001,         # L1 regularization strength
    l2_reg=0.0001          # L2 regularization strength
)

"""## *Model Training with Callbacks*

### utilities
"""

def train_with_advanced_callbacks(model, X_train, y_train, X_val, y_val,
                                 batch_size=32, epochs=100,
                                 early_stopping_patience=10,
                                 reduce_lr_patience=5,
                                 model_checkpoint_path='best_model.h5'):
    """
    Train model with advanced callbacks for better performance

    Parameters:
    -----------
    model : keras.Model
        The compiled model to train
    X_train, y_train : array-like
        Training data and labels
    X_val, y_val : array-like
        Validation data and labels
    batch_size : int, default=32
        Batch size for training
    epochs : int, default=100
        Maximum number of epochs
    early_stopping_patience : int, default=10
        Patience for early stopping
    reduce_lr_patience : int, default=5
        Patience for learning rate reduction
    model_checkpoint_path : str, default='best_model.h5'
        Path to save the best model weights

    Returns:
    --------
    history : dict
        Training history
    """
    # Define callbacks
    callbacks = [
        # Early stopping to prevent overfitting
        EarlyStopping(
            monitor='val_loss',
            patience=early_stopping_patience,
            restore_best_weights=True,
            verbose=1
        ),
        # Reduce learning rate when validation loss plateaus
        ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=reduce_lr_patience,
            min_lr=1e-6,
            verbose=1
        ),
        # Save the best model based on validation loss
        ModelCheckpoint(
            filepath=model_checkpoint_path,
            monitor='val_loss',
            save_best_only=True,
            verbose=1
        )
    ]

    # Train the model
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val),
        epochs=epochs,
        batch_size=batch_size,
        callbacks=callbacks,
        verbose=1
    )

    return history

"""### scripts"""

# Train the model with advanced callbacks
history = train_with_advanced_callbacks(
    model=advanced_model,
    X_train=X_train_seq,
    y_train=y_train,
    X_val=X_val_seq,
    y_val=y_val,
    batch_size=32,
    epochs=100,
    early_stopping_patience=10,
    reduce_lr_patience=5
)

"""## *Model Evaluation*

### utilities
"""

def evaluate_binary_classifier(model, X_test, y_test, class_names=['No Recurrence', 'Recurrence']):
    """
    Comprehensive evaluation of binary classifier with various metrics and plots

    Parameters:
    -----------
    model : keras.Model
        Trained model to evaluate
    X_test, y_test : array-like
        Test data and labels
    class_names : list, default=['No Recurrence', 'Recurrence']
        Names of the classes for plotting

    Returns:
    --------
    dict
        Dictionary of evaluation metrics
    """
    # Get predictions
    y_pred_prob = model.predict(X_test)
    y_pred = (y_pred_prob > 0.5).astype(int)

    # Calculate metrics
    test_loss, test_accuracy, test_auc, test_precision, test_recall = model.evaluate(X_test, y_test, verbose=0)

    # Classification report
    report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)
    print(classification_report(y_test, y_pred, target_names=class_names))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Confusion Matrix')
    plt.colorbar()
    tick_marks = np.arange(len(class_names))
    plt.xticks(tick_marks, class_names)
    plt.yticks(tick_marks, class_names)
    plt.xlabel('Predicted Label')
    plt.ylabel('True Label')

    # Add text annotations to the confusion matrix
    thresh = cm.max() / 2
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(j, i, format(cm[i, j], 'd'),
                    horizontalalignment="center",
                    color="white" if cm[i, j] > thresh else "black")
    plt.tight_layout()
    plt.savefig('confusion_matrix_advanced.png')
    plt.show()

    # ROC curve
    fpr, tpr, _ = roc_curve(y_test, y_pred_prob)
    roc_auc = auc(fpr, tpr)

    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.savefig('roc_curve_advanced.png')
    plt.show()

    # Precision-Recall curve
    precision, recall, _ = precision_recall_curve(y_test, y_pred_prob)
    pr_auc = auc(recall, precision)

    plt.figure(figsize=(8, 6))
    plt.plot(recall, precision, color='blue', lw=2, label=f'PR curve (area = {pr_auc:.2f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend(loc="lower left")
    plt.savefig('pr_curve_advanced.png')
    plt.show()

    # Return all metrics in a dictionary
    metrics = {
        'accuracy': test_accuracy,
        'auc': test_auc,
        'precision': test_precision,
        'recall': test_recall,
        'f1_score': report['weighted avg']['f1-score'],
        'confusion_matrix': cm,
        'roc_auc': roc_auc,
        'pr_auc': pr_auc
    }

    return metrics

"""### scripts"""

# Evaluate the model
metrics = evaluate_binary_classifier(
    model=advanced_model,
    X_test=X_test_seq,
    y_test=y_test
)

print(f"Final model performance:")
print(f"Accuracy: {metrics['accuracy']:.4f}")
print(f"AUC: {metrics['auc']:.4f}")
print(f"F1 Score: {metrics['f1_score']:.4f}")