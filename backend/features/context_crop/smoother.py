class SmoothCamera:
    def __init__(self, alpha=1, min_movement=20):
        """
        Smooth camera movement with dead zone for stability
        alpha: higher value = more stable (default 0.94 for very strong smoothing)
        min_movement: pixels threshold to ignore micro-movements (increased for head movement immunity)
        """
        self.alpha = alpha
        self.prev = None
        self.min_movement = min_movement

    def smooth(self, crop):
        if crop is None:
            return self.prev

        if self.prev is None:
            self.prev = crop
            return crop

        # Check if movement is significant enough to update
        movement = sum(abs(c - p) for p, c in zip(self.prev, crop))
        
        if movement < self.min_movement:
            # Movement is too small, ignore it for stability
            return self.prev

        # Apply exponential smoothing only if movement exceeds threshold
        smooth = tuple(
            int(self.alpha * p + (1 - self.alpha) * c)
            for p, c in zip(self.prev, crop)
        )
        self.prev = smooth
        return smooth
