import torch
from torch import nn
import torch.nn.functional as F
import numpy as np



def G_logistic_ns(fake_logits):
    return -F.logsigmoid(fake_logits).mean() # -log(D(G(z)))


def D_logistic(real_logits, fake_logits):
    return torch.mean(-F.logsigmoid(real_logits) + F.softplus(fake_logits)) # -log(D(x)) - log(1-D(G(z)))



def R1_reg(real_imgs, real_logits):
    '''
    R1 regularization
    '''
    grads = torch.autograd.grad(real_logits.sum(), real_imgs, create_graph=True)[0]
    return torch.mean((grads**2).sum(dim=[1,2,3]))



class Path_length_loss(nn.Module):
    '''
    Path length regularization
    '''
    def __init__(self, decay=0.01):
        super().__init__()
        self.decay = decay
        self.avg = 0

    def forward(self, dlatent, gen_out):
        # Compute |J*y|.
        noise = torch.randn(gen_out.shape, device=gen_out.device)/np.sqrt(np.prod(gen_out.shape[2:])) #[N,Channels,H,W]
        grads = torch.autograd.grad((gen_out * noise).sum(), dlatent, create_graph=True)[0]  #[N, num_layers, dlatent_size]
        lengths = torch.sqrt((grads**2).mean(2).sum(1)) #[N]
        # Update exp average. Lengths are detached
        self.avg = self.decay*torch.mean(lengths.detach()) + (1-self.decay)*self.avg
        return torch.mean((lengths - self.avg)**2)


def Noise_reg(noise_maps, min_res=8):
    '''
    Noise maps regularization to suppress pixel correlation
    '''
    loss = 0
    for nmap in noise_maps:
        res = nmap.shape[-1]
        while res > 8:
            loss += ( torch.mean(nmap * nmap.roll(shifts=1, dims=-1), dim=[-1,-2])**2
                    + torch.mean(nmap * nmap.roll(shifts=1, dims=-2), dim=[-1,-2])**2 ).sum()
            nmap = F.avg_pool2d(nmap.squeeze(), 2)
            res = res//2
    return loss
