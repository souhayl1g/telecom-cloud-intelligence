"""PyTorch VAE architectures for OSS anomaly detection."""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ExperienceVAELegacy(nn.Module):
    """Legacy VAE from early notebook 07 (Sequential encoder/decoder)."""

    def __init__(self, input_dim: int = 10, latent_dim: int = 4, hidden_dim: int = 16):
        super().__init__()
        self.latent_dim = latent_dim
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim // 2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim // 2, latent_dim)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Linear(hidden_dim // 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, input_dim),
        )

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, log_var = self.encode(x)
        z = self.reparameterize(mu, log_var)
        return self.decode(z), mu, log_var

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            recon, _, _ = self.forward(x)
            return F.mse_loss(recon, x, reduction="none").mean(dim=1)


class ExperienceVAE(nn.Module):
    """Original v3.0 VAE from notebook 07 (individual Linear layers)."""

    def __init__(self, input_dim: int = 10, latent_dim: int = 4, hidden_dim: int = 16):
        super().__init__()
        self.latent_dim = latent_dim
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc31 = nn.Linear(hidden_dim // 2, latent_dim)
        self.fc32 = nn.Linear(hidden_dim // 2, latent_dim)
        self.fc4 = nn.Linear(latent_dim, hidden_dim // 2)
        self.fc5 = nn.Linear(hidden_dim // 2, hidden_dim)
        self.fc6 = nn.Linear(hidden_dim, input_dim)

    def encode(self, x):
        h1 = F.relu(self.fc1(x))
        h2 = F.relu(self.fc2(h1))
        return self.fc31(h2), self.fc32(h2)

    def reparameterize(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        h3 = F.relu(self.fc4(z))
        h4 = F.relu(self.fc5(h3))
        return self.fc6(h4)

    def forward(self, x):
        mu, log_var = self.encode(x)
        z = self.reparameterize(mu, log_var)
        return self.decode(z), mu, log_var

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            recon, _, _ = self.forward(x)
            return F.mse_loss(recon, x, reduction="none").mean(dim=1)


class ExperienceVAEv3(nn.Module):
    """Deeper v3.0 VAE from master training (9→32→16→Latent(8))."""

    def __init__(self, input_dim: int = 9, latent_dim: int = 8, hidden_dim: int = 32):
        super().__init__()
        self.latent_dim = latent_dim

        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
        )
        self.fc_mu = nn.Linear(hidden_dim // 2, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim // 2, latent_dim)

        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim // 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_dim, input_dim),
        )

    def encode(self, x):
        h = self.encoder(x)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, log_var):
        std = torch.exp(0.5 * log_var)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        return self.decoder(z)

    def forward(self, x):
        mu, log_var = self.encode(x)
        z = self.reparameterize(mu, log_var)
        return self.decode(z), mu, log_var

    def reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        self.eval()
        with torch.no_grad():
            recon, _, _ = self.forward(x)
            return F.mse_loss(recon, x, reduction="none").mean(dim=1)
