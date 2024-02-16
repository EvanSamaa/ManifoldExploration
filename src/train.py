import torch
from model import *
from utils import *
from inference import *
from blendshapes import *
import json

def train(config: dict):
    if not os.path.exists(config["path"]):
        os.makedirs(config["path"], exist_ok=True)
    json.dump(config, open(os.path.join(
        config["path"], "config.json"), "w+"), indent=4)

    device = torch.device(
        'cuda') if torch.cuda.is_available() else torch.device('cpu')
    
    model = build_model(config)
    model.to(device)
    print(model)
    # load dataset
    dataset = config["training"]["dataset"]
    augment = False
    if "augment" in config["training"]:
        augment = config["training"]["augment"]
    dataset = load_dataset(dataset=dataset, augment=augment)

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

    # tb logger
    import torch.utils.tensorboard as tb
    writer = tb.SummaryWriter(log_dir=config["path"])

    model.train()
    torch.autograd.set_detect_anomaly(True)
    n_blendshapes = config["network"]["n_features"]
    n_epochs = 1000
    from tqdm import tqdm
    pbar = tqdm(range(n_epochs))
    step = 0
    for epoch in pbar:
        for weights in dataset:
            weights = weights.to(device)
            for i in range(n_blendshapes):
                # alpha = torch.rand(weights.shape[0]).to(device).unsqueeze(1)
                alpha = torch.zeros(weights.shape[0]).to(device).unsqueeze(1)
                id = torch.tensor([i] * weights.shape[0]).to(device).unsqueeze(1)
                # id = torch.arange(weights.shape[0]).to(device).unsqueeze(1)
                # print(weights.shape, id.shape, alpha.shape)

                weights_pred = model(weights, alpha, id)
                loss = torch.mean((weights_pred - weights) ** 2)
                writer.add_scalar("loss", loss.item(), step)

                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

                step += 1

            pbar.set_description(f"loss: {loss.item():.4f}", refresh=True)
            save_model(model, config)
    save_model(model, config)

if __name__ == "__main__":
    from utils import *
    from inference import *
    # load the blendshape model
    import os
    PROJ_ROOT = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), os.pardir)
    blendshapes = load_blendshape(model="SP")
    # train
    n_blendshapes = len(blendshapes)
    n_hidden_features = 64
    save_path = os.path.join(PROJ_ROOT, "experiments", "controller")
    dataset = "SP"
    config = {"path": save_path,
              "network": {"type": "controller",
                          "n_features": n_blendshapes,
                          "hidden_features": n_hidden_features,
                          "num_hidden_layers": 5,
                          "nonlinearity": "ReLU"},
              "training": {"dataset": dataset,
                           "loss": {
                               "type": "mse"
                           }}}
    train(config)
