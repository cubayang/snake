# file: PetIBMSimulation.py
# author: Olivier Mesnard (mesnardo@gwu.edu)
# description: Implementation of the class `PetIBMSimulation`.


import os
import sys

import numpy

sys.path.append(os.path.join(os.environ['PETSC_DIR'], 'bin', 'pythonscripts'))
import PetscBinaryIO

from ..barbaGroupSimulation import BarbaGroupSimulation
from ..field import Field
from ..force import Force


class PetIBMSimulation(BarbaGroupSimulation):
  """Contains info about a PetIBM simulation.
  Inherits from the class BarbaGroupSimulation.
  """
  def __init__(self, description=None, directory=os.getcwd(), **kwargs):
    """Initializes by calling the parent constructor.

    Parameters
    ----------
    description: string, optional
      Description of the simulation;
      default: None.
    directory: string, optional
      Directory of the simulation;
      default: present working directory.
    """
    super(PetIBMSimulation, self).__init__(description=description, 
                                           directory=directory, 
                                           software='petibm', 
                                           **kwargs)

  def read_grid(self, file_name='grid.txt'):
    """Reads the coordinates from the file grid.txt.

    Parameters
    ----------
    file_name: string
      Name of file containing grid-node stations along each direction; 
      default: 'grid.txt'.
    """
    print('[info] reading the grid ...'),
    grid_path = '{}/{}'.format(self.directory, file_name)
    with open(grid_path, 'r') as infile:
      n_cells = numpy.array([int(n) for n in infile.readline().strip().split()])
      coords = numpy.loadtxt(infile, dtype=numpy.float64)
    self.grid = numpy.array(numpy.split(coords, numpy.cumsum(n_cells[:-1]+1)))
    print('done')

  def read_forces(self, file_path=None, labels=None):
    """Reads forces from files.

    Parameters
    ----------
    file_path: string, optional
      Path of the file containing the forces data;
      default: None.
    labels: list of strings, optional
      Label to give to each force that will be read from file;
      default: None
    """
    if not file_path:
      file_path = '{}/forces.txt'.format(self.directory)
    print('[info] reading forces from file {} ...'.format(file_path)),
    with open(file_path, 'r') as infile:
      data = numpy.loadtxt(infile, dtype=numpy.float64, unpack=True)
    times = data[0]
    if not labels:
      labels = ['f_x', 'f_z', 'f_z'] # default labels
    for index, values in enumerate(data[1:]):
      self.forces.append(Force(times, values, label=labels[index]))
    print('done')

  def read_fluxes(self, time_step, periodic_directions=[]):
    """Reads the flux fields at a given time-step.

    Parameters
    ----------
    time_step: integer
      Time-step at which the field will be read.
    periodic_directions: list of strings, optional
      Directions that have periodic boundary conditions; 
      default: [].
    """
    print('[time-step {}] reading fluxes from files ...'.format(time_step)),
    dim3 = (len(self.grid) == 3)
    # folder with numerical solution
    folder = '{}/{:0>7}'.format(self.directory, time_step)
    # read grid-stations and fluxes
    x, y = self.grid[:2]
    nx, ny = x.size-1, y.size-1
    qx = PetscBinaryIO.PetscBinaryIO().readBinaryFile('{}/qx.dat'.format(folder))[0]
    qy = PetscBinaryIO.PetscBinaryIO().readBinaryFile('{}/qy.dat'.format(folder))[0]
    if dim3:
      z = self.grid[2]
      nz = z.size-1
      qz = PetscBinaryIO.PetscBinaryIO().readBinaryFile('{}/qz.dat'.format(folder))[0]
    # create flux Field objects in staggered arrangement
    # reshape fluxes in multi-dimensional arrays
    if dim3:
      qx = qx.reshape((nz, ny, (nx if 'x' in periodic_directions else nx-1)))
      qx = qx[:, :, :(-1 if 'x' in periodic_directions else None)]
      qx = Field(label='x-flux',
                 time_step=time_step,
                 x=x[1:-1], 
                 y=0.5*(y[:-1]+y[1:]), 
                 z=0.5*(z[:-1]+z[1:]), 
                 values=qx)
      qy = qy.reshape((nz, (ny if 'y' in periodic_directions else ny-1), nx))
      qy = qy[:, :(-1 if 'y' in periodic_directions else None), :]
      qy = Field(label='y-flux',
                 time_step=time_step,
                 x=0.5*(x[:-1]+x[1:]), 
                 y=y[1:-1], 
                 z=0.5*(z[:-1]+z[1:]), 
                 values=qy)
      qz = qz.reshape(((nz if 'z' in periodic_directions else nz-1), ny, nx))
      qz = qz[:(-1 if 'z' in periodic_directions else None), :, :]
      qz = Field(label='z-flux',
                 time_step=time_step,
                 x=0.5*(x[:-1]+x[1:]), 
                 y=0.5*(y[:-1]+y[1:]), 
                 z=z[1:-1], 
                 values=qz)
      print('done')
      return qx, qy, qz
    else:
      qx = qx.reshape((ny, (nx if 'x' in periodic_directions else nx-1)))
      qx = qx[:, :(-1 if 'x' in periodic_directions else None)]
      qx = Field(label='x-flux',
                 time_step=time_step,
                 x=x[1:-1],
                 y=0.5*(y[:-1]+y[1:]),
                 values=qx)
      qy = qy.reshape(((ny if 'y' in periodic_directions else ny-1), nx))
      qy = qy[:(-1 if 'y' in periodic_directions else None), :]
      qy = Field(label='y-flux',
                 time_step=time_step,
                 x=0.5*(x[:-1]+x[1:]),
                 y= y[1:-1],
                 values=qy)
      print('done')
      return qx, qy

  def read_pressure(self, time_step):
    """Reads the pressure field from file given the time-step.

    Parameters
    ----------
    time_step: integer
      Time-step at which the field will be read.
    """
    print('[time-step {}] reading pressure field ...'.format(time_step)),
    dim3 = (len(self.grid) == 3)
    # get grid stations and number of cells along each direction
    x, y = self.grid[:2]
    nx, ny = x.size-1, y.size-1
    if dim3:
      z = self.grid[2]
      nz = z.size-1
    # folder with numerical solution
    folder = '{}/{:0>7}'.format(self.directory, time_step)
    # read pressure
    p = PetscBinaryIO.PetscBinaryIO().readBinaryFile('{}/phi.dat'.format(folder))[0]
    # set pressure Field object
    if dim3:
      p = Field(label='pressure',
                time_step=time_step,
                x=0.5*(x[:-1]+x[1:]), 
                y=0.5*(y[:-1]+y[1:]), 
                z=0.5*(z[:-1]+z[1:]), 
                values=p.reshape((z.size-1, y.size-1, x.size-1)))
    else:
      p = Field(label='pressure',
                time_step=time_step,
                x=0.5*(x[:-1]+x[1:]), 
                y=0.5*(y[:-1]+y[1:]), 
                values=p.reshape((y.size-1, x.size-1)))
    print('done')
    return p