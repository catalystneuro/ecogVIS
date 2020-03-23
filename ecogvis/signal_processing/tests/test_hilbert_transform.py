import numpy as np
from ecogvis.signal_processing.hilbert_transform import (hilbert_transform,
        gaussian, hamming)
import unittest

class HilbertTestCase(unittest.TestCase):

    def setUp(self):
        self.X = np.array([-1.90326482,  0.35096703,  1.26193713,  1.35437749, -1.01596516,
                       -0.01740816,  1.40755137, -1.87826967,  0.25096001,  0.52397222,
                       -0.33671476, -2.59298705,  0.18516219,  0.36746056,  0.41544204,
                        1.86434848, -0.45742732,  0.39596267,  0.27323786,  0.55796332,
                        0.55035036,  0.42901251,  2.04574957,  0.29213717, -0.71105487,
                       -0.63116681,  1.57401261,  1.3785037 ,  0.17613027,  1.58919257,
                       -0.16175437, -0.5684704 ,  0.41837715, -0.17657268,  1.01687025,
                        0.27467374,  1.65216317, -0.76683111,  0.11962773, -1.77906483,
                        0.78977701, -0.21193541,  0.09266877, -0.6837059 , -0.14342515,
                        0.71256218,  2.18441782,  1.22294831,  0.7248046 ,  0.24423127])
        self.rate = 20

        
    def test_hilbert_return(self):
        
        
        filters = [gaussian(self.X, self.rate, 10, 2),
                   hamming(self.X, self.rate, 10, 15)]
        Xh = hilbert_transform(self.X, self.rate, filters)
        
        Xh_expected = (np.array([[-0.21311015-0.0607549j ,  0.19600701-0.01539358j,
             -0.173067  +0.05698152j,  0.16533213-0.11073435j,
             -0.11528449+0.19558509j, -0.01099088-0.23956958j,
              0.14327258+0.17653984j, -0.18458968-0.04880616j,
              0.13415315-0.03647032j, -0.0869473 +0.04084354j,
              0.10334343-0.03818917j, -0.12906154+0.10043456j,
              0.08385944-0.19477458j,  0.03056594+0.24082505j,
             -0.15400577-0.2042584j ,  0.22998364+0.10362084j,
             -0.23235176+0.0114163j ,  0.18106783-0.09160866j,
             -0.11846912+0.12803714j,  0.0616374 -0.14137947j,
             -0.00263204+0.13730891j, -0.05106666-0.10123634j,
              0.06800086+0.04061233j, -0.04404788+0.00171742j,
              0.0226942 -0.0115417j , -0.0187925 +0.03051893j,
             -0.01429313-0.07107013j,  0.09650135+0.07795065j,
             -0.174921  -0.01024875j,  0.18714607-0.10299498j,
             -0.12381878+0.19594172j,  0.0300773 -0.22737868j,
              0.04435296+0.21050902j, -0.08900898-0.18207646j,
              0.12224477+0.15960843j, -0.15896489-0.13540482j,
              0.19442573+0.09691784j, -0.21726567-0.04694222j,
              0.22820716-0.00885319j, -0.22209987+0.07472441j,
              0.18310959-0.13794065j, -0.12027016+0.17057613j,
              0.06293843-0.16911559j, -0.02503065+0.15016524j,
              0.01000077-0.12699406j, -0.0166137 +0.12012645j,
              0.01741438-0.1460833j ,  0.02050994+0.18394571j,
             -0.09605629-0.19316342j,  0.17592968+0.14807635j],
            [ 0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ,
              0.        +0.j        ,  0.        +0.j        ]]),
     np.array([[ 12.66153466 +0.j        ,  -8.52937982 +2.82208427j,
              14.7942873  +7.52162635j,  11.10045364 +3.52566249j,
              -4.45306874 +1.51630448j, -15.9713513  +6.17519069j,
             -12.79444213 -3.10589728j,   7.48901625 +4.52892871j,
             -26.31533498-14.97259445j, -13.34218938 -5.91763703j,
              -6.37207362 -7.78666016j,   9.73243576 +0.81983001j,
              -7.31044034-10.82940129j, -13.95317074 +6.17574407j,
             -13.04640635 -4.2499415j ,  -8.50946101+23.85947587j,
               3.63491644 +8.31427148j,  10.54954233 +5.55684696j,
              -7.73593253 -7.06994243j,  -3.63069263 -4.01064809j,
              -0.58244679 -0.45476267j,   0.3190497 -17.87031979j,
             -16.3983279 +10.94541315j, -15.21443532 +3.27680235j,
               0.55694424 -9.41396278j,   0.         +0.j        ,
               0.         +0.j        ,   0.         -0.j        ,
               0.         -0.j        ,   0.         +0.j        ,
              -0.         +0.j        ,  -0.         +0.j        ,
              -0.         +0.j        ,   0.         +0.j        ,
               0.         +0.j        ,   0.         -0.j        ,
              -0.         +0.j        ,   0.         -0.j        ,
              -0.         +0.j        ,   0.         +0.j        ,
              -0.         +0.j        ,  -0.         +0.j        ,
              -0.         +0.j        ,   0.         +0.j        ,
              -0.         +0.j        ,   0.         -0.j        ,
               0.         -0.j        ,   0.         +0.j        ,
               0.         +0.j        ,   0.         -0.j        ]]))
        
        assert np.allclose(Xh[0],Xh_expected[0])
        assert np.allclose(Xh[1],Xh_expected[1])

        Xh = hilbert_transform(self.X, self.rate)
        
        Xh_expected = (np.array([-2.06641947-0.01287173j,  0.51412168-1.48267793j,
             1.09878248-0.2770345j ,  1.51753214+1.04348296j,
            -1.17911981+1.40558571j,  0.14574649-1.35839109j,
             1.24439672+1.55083418j, -1.71511502+0.64355861j,
             0.08780536-1.05022613j,  0.68712687+0.47911231j,
            -0.49986941+1.32336045j, -2.4298324 -0.32441863j,
             0.02200754-2.43445411j,  0.53061521-0.23437869j,
             0.25228739-1.73350628j,  2.02750313+0.27984872j,
            -0.62058197+0.45810456j,  0.55911732-0.78389594j,
             0.11008321-0.06264994j,  0.72111797-0.74545203j,
             0.38719571+0.13653827j,  0.59216716-1.05822436j,
             1.88259492+0.22982255j,  0.45529182+1.40341331j,
            -0.87420952+0.45050791j, -0.46801216-1.17055015j,
             1.41085796-1.23975681j,  1.54165835+0.78468877j,
             0.01297562+0.11350984j,  1.75234722+0.23771566j,
            -0.32490902+1.84850866j, -0.40531575-0.56893904j,
             0.2552225 +0.44197517j, -0.01341803-0.68464856j,
             0.8537156 +0.27623658j,  0.43782839-0.38555419j,
             1.48900852+1.13057857j, -0.60367646+1.05556027j,
            -0.04352692+0.77890928j, -1.61591018-0.01930377j,
             0.62662236-1.11621127j, -0.04878076+0.60438919j,
            -0.07048588-0.4217956j , -0.52055125+0.12783525j,
            -0.3065798 -1.47275369j,  0.87571683-1.19296222j,
             2.02126317-0.75806081j,  1.38610296+1.35508274j,
             0.56164995+0.43484911j,  0.40738592+1.99470883j]),
     np.array([[ 12.66153466 +0.j        ,  -8.52937982 +2.82208427j,
              14.7942873  +7.52162635j,  11.10045364 +3.52566249j,
              -4.45306874 +1.51630448j, -15.9713513  +6.17519069j,
             -12.79444213 -3.10589728j,   7.48901625 +4.52892871j,
             -26.31533498-14.97259445j, -13.34218938 -5.91763703j,
              -6.37207362 -7.78666016j,   9.73243576 +0.81983001j,
              -7.31044034-10.82940129j, -13.95317074 +6.17574407j,
             -13.04640635 -4.2499415j ,  -8.50946101+23.85947587j,
               3.63491644 +8.31427148j,  10.54954233 +5.55684696j,
              -7.73593253 -7.06994243j,  -3.63069263 -4.01064809j,
              -0.58244679 -0.45476267j,   0.3190497 -17.87031979j,
             -16.3983279 +10.94541315j, -15.21443532 +3.27680235j,
               0.55694424 -9.41396278j,   0.         +0.j        ,
               0.         +0.j        ,   0.         -0.j        ,
               0.         -0.j        ,   0.         +0.j        ,
              -0.         +0.j        ,  -0.         +0.j        ,
              -0.         +0.j        ,   0.         +0.j        ,
               0.         +0.j        ,   0.         -0.j        ,
              -0.         +0.j        ,   0.         -0.j        ,
              -0.         +0.j        ,   0.         +0.j        ,
              -0.         +0.j        ,  -0.         +0.j        ,
              -0.         +0.j        ,   0.         +0.j        ,
              -0.         +0.j        ,   0.         -0.j        ,
               0.         -0.j        ,   0.         +0.j        ,
               0.         +0.j        ,   0.         -0.j        ]]))
        
        assert np.allclose(Xh[0],Xh_expected[0])
        assert np.allclose(Xh[1],Xh_expected[1])


    def test_gaussian(self):
       
        center = 10
        sd = 2
        Xg = gaussian(self.X, self.rate, center, sd)
        Xg_expected = np.array([1.25183332e-06, 3.33545509e-06, 8.53870306e-06, 2.10018206e-05,
           4.96306770e-05, 1.12686444e-04, 2.45822352e-04, 5.15227799e-04,
           1.03754137e-03, 2.00742710e-03, 3.73166252e-03, 6.66489268e-03,
           1.14370016e-02, 1.88564278e-02, 2.98699767e-02, 4.54609562e-02,
           6.64768556e-02, 9.33964981e-02, 1.26072086e-01, 1.63506681e-01,
           2.03741870e-01, 2.43923305e-01, 2.80578586e-01, 3.10087294e-01,
           3.29262021e-01, 3.35913555e-01, 3.29262021e-01, 3.10087294e-01,
           2.80578586e-01, 2.43923305e-01, 2.03741870e-01, 1.63506681e-01,
           1.26072086e-01, 9.33964981e-02, 6.64768556e-02, 4.54609562e-02,
           2.98699767e-02, 1.88564278e-02, 1.14370016e-02, 6.66489268e-03,
           3.73166252e-03, 2.00742710e-03, 1.03754137e-03, 5.15227799e-04,
           2.45822352e-04, 1.12686444e-04, 4.96306770e-05, 2.10018206e-05,
           8.53870306e-06, 3.33545509e-06])
        
        assert np.allclose(Xg,Xg_expected)


    def test_hamming(self):
        
        min_freq = 10
        max_freq = 15
        Xham = hamming(self.X, self.rate, min_freq, max_freq)
        Xham_expected = np.array([0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.,
           0., 0., 0., 0., 0., 0., 0., 0., 1., 0., 0., 0., 0., 0., 0., 0., 0.,
           0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0., 0.])
        assert np.allclose(Xham,Xham_expected)
        

