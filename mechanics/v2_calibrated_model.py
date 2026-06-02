import math

class V2CalibratedModel:
    def __init__(self, v1_model, weights=None):
        self.v1_model = v1_model
        self.weights = weights or {"w1": 1.0, "w2": 0.1, "bias": 0.0}

    def sigmoid(self, x):
        return 1 / (1 + math.exp(-x))

    def predict_outcome(self, attacker, defender, features=None):
        v1_result = self.v1_model.predict(attacker, defender)
        
        # Simple feature vector representation
        feature_val = sum(features) if features else 0
        
        # P(win) = sigmoid(V1_output * W1 + feature_vector * W2 + bias)
        # Using winner as a proxy for V1_output (1 for attacker, -1 for defender)
        v1_score = 1.0 if v1_result['winner'] == 'attacker' else -1.0
        
        z = (v1_score * self.weights['w1']) + (feature_val * self.weights['w2']) + self.weights['bias']
        win_probability = self.sigmoid(z)
        
        return {
            "v1_result": v1_result,
            "win_probability": win_probability,
            "predicted_winner": "attacker" if win_probability > 0.5 else "defender"
        }
