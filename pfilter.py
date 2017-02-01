import numpy as np
# return a new function that has the heat kernel (given by delta) applied.
def make_heat_adjusted(sigma):
    def heat_distance(d):
        return np.exp(-d**2 / (2.0*sigma**2))
    return heat_distance

# resample function from http://scipy-cookbook.readthedocs.io/items/ParticleFilter.html    
def resample(weights):
  n = len(weights)
  indices = []
  C = [0.] + [np.sum(weights[:i+1]) for i in range(n)]
  u0, j = np.random.random(), 0
  for u in [(u0+i)/n for i in range(n)]:
    while u > C[j]:
      j+=1
    indices.append(j-1)
  return indices    
  
  
def no_dynamics(x):
    return x
    
def no_noise(x):
    return x
    
def squared_error(x,y,sigma=1):
    # RBF kernel
    d = np.sum((x-y)**2, axis=(1,2))
    return np.exp(-d / (2.0*sigma**2))
    
def gaussian_noise(x, sigmas):    
    n = np.random.normal(np.zeros(len(sigmas)), sigmas, size=(x.shape[0], len(sigmas)))
    return x+n

class ParticleFilter(object):
    def __init__(self, priors,  inverse_fn, n_particles=200, dynamics_fn=None, noise_fn=None, 
                weight_fn=None, resample_proportion=0.05, column_names=None):
        """
        
        Parameters:
        ---
        
        priors: sequence of prior distributions; should be a frozen distribution from scipy.stats; 
                e.g. scipy.stats.norm(loc=0,scale=1) for unit normal
        inverse_fn: transformation function from the internal state to the sensor state. Takes an (N,D) array of states 
                    and returns the expected sensor output as an array (e.g. a tensor).
        n_particles: number of particles in the filter
        dynamics_fn: dynamics function, which takes a state vector and returns a new one with the dynamics applied.
        noise_fn: noise function, takes a state vector and returns a new one with noise added.
        weight_fn: computes the distance from the real sensed variable and that returned by inverse_fn. Takes
                  a an array of N sensor outputs and the observed output (x,y) and 
                  returns a strictly positive weight for the output. This should be a *similarity* measure, 
                  with higher values meaning more similar
        
        """
        self.column_names = column_names
        self.priors = priors
        self.d = len(self.priors)
        self.n_particles = n_particles
        self.inverse_fn = inverse_fn
        self.dynamics_fn = dynamics_fn or no_dynamics
        self.noise_fn = noise_fn or no_noise
        self.weight_fn = weight_fn or squared_error
        self.resample_proportion = resample_proportion
        self.particles = np.zeros((self.n_particles, self.d))
        
    def init_filter(self, mask=None):
        # resample from the prior
        if mask is None:
            for i,prior in enumerate(self.priors):
                self.particles[:,i] = prior.rvs(self.n_particles)
        else:
            for i,prior in enumerate(self.priors):
                self.particles[mask,i] = prior.rvs(self.n_particles)[mask]
    
    def update(self, observed):
        # apply dynamics and noise
        self.particles = self.dynamics_fn(self.particles)
        self.particles = self.noise_fn(self.particles)
        
        # invert to hypothesise observations
        hypotheses = self.inverse_fn(self.particles)
        self.hypotheses = hypotheses
        
        # compute similarity to observations
        weights = self.weight_fn(hypotheses, observed)
        
        
        # force to be positive and normalise to "probabilities"
        weights = np.clip(weights, 0, np.inf)        
        self.weights = weights / np.sum(weights)
        
        
        
        # resampling step
        indices = resample(self.weights)
        self.particles = self.particles[indices, :]
        
        # mean hypothesis
        self.mean_hypothesis = np.sum(self.hypotheses.T * self.weights, axis=-1).T
        self.mean_state = np.sum(self.particles.T * self.weights, axis=-1).T
        
        # randomly resample some particles from the prior
        random_mask = np.random.random(size=(self.n_particles,))<self.resample_proportion
        self.resampled_particles = random_mask
        self.init_filter(mask=random_mask)
        
# from scipy.stats import norm, gamma, uniform 
# priors = [uniform(loc=0, scale=32), uniform(loc=0, scale=32), gamma(a=2,loc=0,scale=10)]

# testing only
# import skimage.draw
# import cv2
# def blob(x):
    # y = np.zeros((x.shape[0], 32, 32))
    # for i,particle in enumerate(x):
        # rr,cc = skimage.draw.circle(particle[0], particle[1], particle[2], shape=(32,32))
        # y[i,rr,cc] = 1
    # return y
        

# def test_filter():
    # pf = ParticleFilter(priors=priors, 
                    # inverse_fn=blob,
                    # n_particles=200,
                    # noise_fn=lambda x: gaussian_noise(x, sigmas=[0.3, 0.3, 0.1]),
                    # weight_fn=lambda x,y:squared_error(x, y,sigma=2),
                    # resample_proportion=0.1)
                    
    # x,y,s = 12,18,np.random.uniform(3,6)
    # dx = np.random.uniform(-0.1,0.1)
    # dy = np.random.uniform(-0.1,0.1)    
    # cv2.namedWindow('img',cv2.WINDOW_NORMAL)
    # cv2.namedWindow('samples',cv2.WINDOW_NORMAL)
    # cv2.resizeWindow('img', 320,320)
    # cv2.resizeWindow('samples', 320,320)
    # for i in range(1000):        
        # img = blob(np.array([[x,y,s]]))
        # pf.update(img)
        # cv2.imshow("img", np.squeeze(img))
        
        
        # cv2.imshow("samples", pf.mean_hypothesis)
        # cv2.waitKey(20)
        # x+=dx
        # y+=dy
        # print np.mean(pf.particles, axis=0)
    # cv2.destroyAllWindows()
# test_filter()
