# incorporating the neural network parameters and save the trained models
# no modification needed

import os
import shutil
import sys

import torch
import torch.nn as nn

from baseline_net import BaselineNet
from utils import load_yaml
from torch.optim import lr_scheduler

cfg = load_yaml("master_config.yaml")["training"]
os.environ["CUDA_VISIBLE_DEVICES"] = cfg["gpu_ids"]


class NNState:
    """
    THIS SCRIPT DOES NOT REQUIRE MODIFICATION

    This class functions to load the weights and hyper-parameters onto the
    network structured declared in ./net_model/*.py or and to save weights and
    hyper-parameters.
    """

    def __init__(self, mode, params=None):
        lr_step_size = cfg["lr_scheduler"]["step_size"]
        lr_gamma = cfg["lr_scheduler"]["gamma"]
        decay = cfg["weight_decay"]
        if params == None:
            self.batch_size = cfg["batch_size"]
            self.n_epochs = cfg["n_epochs"]
            self.init_lr = cfg["init_lr"]
            self.exp_name = cfg["exp_name"]
            self.num_workers = 0
            print(f"Using values in master_config.yaml")
        else:
            self.batch_size = params["batch_size"]
            self.n_epochs = params["n_epochs"]
            self.init_lr = params["init_lr"]
            self.exp_name = params["exp_name"]
            self.num_workers = params["num_workers"]
            lr_step_size = params["lr_scheduler"]["step_size"]
            lr_gamma = params["lr_scheduler"]["gamma"]
            decay = params["weight_decay"]
            print(f"Successfully loaded custom params")

        self.device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
        self.net = BaselineNet(cfg["num_classes"]).to(self.device)

        self.best_acc = 10000
        self.last_epoch = -1
        # using Adam optimization
        self.optimiser = torch.optim.Adam(
            self.net.parameters(), lr=self.init_lr, weight_decay=decay
        )
        self.lr_scheduler = lr_scheduler.StepLR(
            self.optimiser, gamma=lr_gamma, step_size=lr_step_size
        )
        self.criterion = torch.nn.CrossEntropyLoss()
        self.gpu_count = torch.cuda.device_count()
        if mode != "eval" and mode != "train":
            sys.exit("NN Mode Not Supported, Choose Between 'train' and 'eval'")
        else:
            self.mode = mode
            self.config_nn_state()

    def config_nn_state(self):
        best = cfg["load_best"]
        if best:
            ckpt_name = "%s_best.pth.tar" % self.exp_name
        else:
            ckpt_name = "%s_ckpt.pth.tar" % self.exp_name
        model_path = os.path.join("net_weights", self.exp_name, ckpt_name)
        ckpt_exists = os.path.exists(model_path)
        if ckpt_exists:
            # ckpt = torch.load(model_path)
            ckpt = torch.load(model_path, map_location=lambda storage, loc: storage)
            self.net.load_state_dict(ckpt["net_param"])
            if self.gpu_count > 1:
                print("Training with %i GPUs" % self.gpu_count)
                self.net = nn.DataParallel(self.net)
            self.last_epoch = ckpt["last_epoch"]
            self.optimiser.load_state_dict(ckpt["optimiser"])
            self.lr_scheduler.load_state_dict(ckpt["lr_scheduler"])
            self.best_acc = ckpt["best_acc"]
            print(
                "=> Loaded %s,\n   Trained till %dth Epochs"
                % (ckpt_name, self.last_epoch)
            )
            if self.mode == "eval":
                self.net = self.net.eval()
            elif self.mode == "train":
                self.net = self.net.train()
        else:
            if self.mode == "train" and self.gpu_count > 1:
                print("Training with %i GPUs" % self.gpu_count)
                self.net = nn.DataParallel(self.net)
            elif self.mode == "eval":
                sys.exit("=> Checkpoint Doesn't Exist, Terminated")

    def save_ckpt(self, current_epoch, delta_acc=0):
        """Save checkpoint if a new best is achieved"""
        if self.gpu_count > 1:
            net_param = self.net.module.state_dict()
        else:
            net_param = self.net.state_dict()
        state = {
            "last_epoch": current_epoch,
            "net_param": net_param,
            "optimiser": self.optimiser.state_dict(),
            "lr_scheduler": self.lr_scheduler.state_dict(),
            "best_acc": self.best_acc,
        }
        ckpt_name = "%s_ckpt.pth.tar" % self.exp_name
        folder_path = os.path.join("net_weights", self.exp_name)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        ckpt_path = os.path.join("net_weights", self.exp_name, ckpt_name)
        torch.save(state, ckpt_path)  # save checkpoint
        print(f"=> Model Saved in {ckpt_path}")
        if delta_acc > 0:
            best_model_name = "%s_best.pth.tar" % self.exp_name
            best_file_path = os.path.join("net_weights", self.exp_name, best_model_name)
            shutil.copyfile(ckpt_path, best_file_path)
            print("=> Best Model Updated,\n     %.3f Mean Loss Reduction" % delta_acc)

    def to_device(self, var):
        var = var.to(self.device)
        return var
