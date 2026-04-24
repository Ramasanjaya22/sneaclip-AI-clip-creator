try:
    from torch import nn
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    nn = None
    torch = None
    TORCH_AVAILABLE = False


try:
    import torch_directml
    DIRECTML_AVAILABLE = True
except ImportError:
    torch_directml = None
    DIRECTML_AVAILABLE = False


class FallbackModel:
    def __init__(self):
        self.is_fallback = True


def get_directml_device():
    if DIRECTML_AVAILABLE and torch_directml:
        return torch_directml.device()
    return None


def load_model(model, weights_path, device="cpu"):
    if not TORCH_AVAILABLE:
        return FallbackModel()

    try:
        model.load_state_dict(torch.load(weights_path, weights_only=True, map_location="cpu"))

        is_dml = str(device).startswith("privateuseone") or (
            DIRECTML_AVAILABLE and torch_directml and device == torch_directml.device()
        )

        if is_dml:
            for name, module in model.named_children():
                if name == "LSTM":
                    continue
                module.to(device)
        else:
            model.to(device)

        model.eval()

        test_input = torch.randn(1, 40, 100).to(device)
        with torch.no_grad():
            _ = model(test_input)

        return model, device
    except Exception as e:
        print(f"Warning: Failed to load model on {device}, falling back to CPU. Error: {e}")
        model.cpu()
        model.eval()
        return model, "cpu"


if TORCH_AVAILABLE:
    class Conv1dBlock(nn.Module):
        def __init__(self, in_features, out_features, kernel_size=3, stride=1, padding=1, dilation=1):
            super().__init__()

            self.conv1d = nn.Conv1d(in_features, out_features, kernel_size=kernel_size, stride=stride, padding=padding, dilation=dilation)
            self.instancenorm = nn.InstanceNorm1d(out_features, affine=True)
            self.relu = nn.ReLU()

        def forward(self, X):
            X = self.conv1d(X)
            X = self.instancenorm(X)
            X = self.relu(X)

            return X


    class VideoAutoClipper(nn.Module):
        def __init__(self):
            super().__init__()

            self.conv1dblock_1 = Conv1dBlock(40, 64)
            self.conv1dblock_2 = Conv1dBlock(64, 128, kernel_size=3, padding=2, dilation=2)

            self.conv1dblock_3 = Conv1dBlock(128, 256, kernel_size=3, padding=4, dilation=4)
            self.conv1dblock_4 = Conv1dBlock(256, 512, kernel_size=3, padding=8, dilation=8)

            self.conv1dblock_5 = Conv1dBlock(512, 1024, kernel_size=3, padding=8, dilation=8)
            self.LSTM = nn.LSTM(1024, 1024, batch_first=True, bidirectional=True)

            self.conv1dblock_6 = Conv1dBlock(2048, 4096, kernel_size=1, padding=0)
            self.conv1dblock_7 = Conv1dBlock(4096, 8192, kernel_size=3, padding=8, dilation=8)

            self.conv1dblock_8 = Conv1dBlock(8192, 4096, kernel_size=3, padding=8, dilation=8)
            self.conv1dblock_9 = Conv1dBlock(4096, 2048, kernel_size=3, padding=8, dilation=8)

            self.conv1dblock_10 = Conv1dBlock(2048, 1024, kernel_size=3, padding=2, dilation=2)
            self.conv1dblock_11 = Conv1dBlock(1024, 512, kernel_size=3, padding=2, dilation=2)
        
            self.conv1dblock_12 = Conv1dBlock(512, 256, kernel_size=1, padding=0)
            self.dropout = nn.Dropout(0.5)
            self.conv1dfinal = nn.Conv1d(256, 1, kernel_size=1, padding=0)

        def _is_dml(self, tensor):
            return tensor.device.type == "privateuseone"

        def forward(self, X):
            on_dml = self._is_dml(X)

            X = self.conv1dblock_1(X)
            X = self.conv1dblock_2(X)

            X = self.conv1dblock_3(X)
            X = self.conv1dblock_4(X)

            X = self.conv1dblock_5(X)

            if on_dml:
                X = X.cpu()
            X, _ = self.LSTM(X.view(X.size(0), X.size(2), X.size(1)))
            if on_dml:
                X = X.to(self.conv1dblock_6.conv1d.weight.device)

            X = self.conv1dblock_6(X.view(X.size(0), X.size(2), X.size(1)))
            X = self.conv1dblock_7(X)

            X = self.conv1dblock_8(X)
            X = self.conv1dblock_9(X)

            X = self.conv1dblock_10(X)
            X = self.conv1dblock_11(X)

            X = self.conv1dblock_12(X)
            X = self.dropout(X)
            X = self.conv1dfinal(X)

            return X.squeeze()
else:
    class Conv1dBlock:
        def __init__(self, *args, **kwargs):
            pass


    class VideoAutoClipper:
        def __init__(self):
            self.is_fallback = True
