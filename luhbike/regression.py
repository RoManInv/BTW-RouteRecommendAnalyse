import sys
from typing import List, Tuple, Union
sys.path.insert(0, ".")
import statistics

import pandas as pd
from autogluon.tabular import TabularDataset, TabularPredictor
from sklearn.model_selection import train_test_split, StratifiedGroupKFold, GroupKFold
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from itertools import islice

import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from dbaccess.dbconn import dbconn

_COL_NAMES_= ["ride_id", "lat", "lon", "x", "y", "z", "duration", "acc", "a", "b", "c", "obsdistanceleft1", "obsdistanceleft2", "obsdistanceright1", "obsdistanceright2", "obsclosepassevent", "xl", "yl", "zl", "rx", "ry", "rz", "rc", "year", "month", "day", "hour", "osm_id", "geo_point", "gml_id", "sobj_kz", "segm_segm", "segm_bez", "stst_str", "stor_name", "ortstl", "rva_typ", "sorvt_typ", "laenge", "b_pflicht", "edge_geo_3857", "occurrences", "avg_speed_kmh", "access", "addr:housename", "addr:housenumber", "addr:interpolation", "admin_level", "aerialway", "aeroway", "amenity", "area", "barrier", "bicycle", "brand", "bridge", "boundary", "building", "construction", "covered", "culvert", "cutting", "denomination", "disused", "embankment", "foot", "generator:source", "harbour", "highway", "historic", "horse", "intermittent", "junction", "landuse", "layer", "leisure", "lock", "man_made", "military", "motorcar", "name", "natural", "office", "oneway", "operator", "place", "population", "power", "power_source", "public_transport", "railway", "ref", "religion", "route", "service", "shop", "sport", "surface", "toll", "tourism", "tower:type", "tracktype", "tunnel", "water", "waterway", "wetland", "width", "wood", "z_order", "way_area", "way", "airtemp", "rel_humid", "temp_2cm", "temp_5cm", "temp_10cm", "temp_20cm", "temp_50cm", "temp_100cm", "precipitation_1h", "precipitation_indicator", "precipitation_type", "dur_sunshine", "wind_spd", "wind_direction", "label", "rva_typ_Radfahrstreifen", "rva_typ_Bussonderfahrstreifen", "rva_typ_", "rva_typ_Schutzstreifen", "rva_typ_Radwege", "sorvt_typ_Radfahrstreifen Z 295, ruh.Verkehr mit Begrenzung", "sorvt_typ_Radverkehrsanlage Z 340 im/am Knotenpunktsbereich", "sorvt_typ_Gehweg, mit Radverkehr frei", "sorvt_typ_Bussonderfahrstreifen Z 295", "sorvt_typ_Geh-/Radweg, durch Markierung unterschieden", "sorvt_typ_Radweg, baulich getrennt", "sorvt_typ_Radfahrerfurt Z 340", "sorvt_typ_Schutzstreifen Z 340 ohne ruhenden Verkehr", "sorvt_typ_Geh-/Radweg, baulich unterschieden", "sorvt_typ_Schutzstreifen Z 340, mit ruh.Verkehr ohne Begrenzung", "sorvt_typ_Radfahrstreifen Z 295, ohne ruh.Verkehr", "sorvt_typ_Geh-/Radweg, ohne Trennung", "sorvt_typ_Bussonderfahrstreifen Z 340", "sorvt_typ_Schutzstreifen Z 340, mit ruh.Verkehr mit Begrenzung", "bicycle_discouraged", "bicycle_use_sidepath", "bicycle_designated", "bicycle_yes", "bicycle_optional_sidepath", "bicycle_no", "construction_bridge", "construction_rail", "construction_yes", "construction_light_rail", "construction_None", "construction_tram", "cutting_None", "cutting_yes", "foot_no", "foot_use_sidepath", "foot_designated", "foot_yes", "junction_None", "junction_roundabout", "junction_circular", "highway_trunk", "highway_footway", "highway_platform", "highway_secondary", "highway_secondary_link", "highway_pedestrian", "highway_primary", "highway_residential", "highway_track", "highway_primary_link", "highway_motorway_link", "highway_service", "highway_motorway", "highway_path", "place_suburb", "place_city", "place_borough", "railway_platform", "railway_subway", "railway_rail", "railway_light_rail", "railway_abandoned", "railway_construction", "railway_platform_edge", "railway_tram", "railway_proposed", "railway_narrow_gauge", "railway_razed", "railway_disused", "service_driveway", "service_regional", "service_yard", "service_crossover", "service_spur", "service_siding", "surface_concrete:plates", "surface_dirt", "surface_gravel", "surface_sett", "surface_cobblestone", "surface_compacted", "surface_paving_stones", "surface_cobblestone:flattened", "surface_concrete", "surface_asphalt", "surface_sand", "tunnel_no", "tunnel_building_passage", "tunnel_yes", "final", "oneway_yes", "oneway_no", "speed", "absl", "absr", "label_reg"]

__VERBOSE__ = 2



class ModelTrainPreprocessor():
    def __init__(self, DBconn = None) -> None:
        if(not DBconn):
            self.__dbconn = dbconn.connect()
            self.__cur = self.__dbconn.cursor()
        else:
            self.__dbconn = DBconn
            self.__cur = self.__dbconn.cursor()

    def getAllData(self) -> pd.DataFrame:
        _sql = """
               SELECT * FROM berlin_final
               """
        self.__cur.execute(_sql)
        data = pd.DataFrame(self.__cur.fetchall(), columns = _COL_NAMES_)
        # print(data.head())
        return data
    
    def dropEmptyVal(self, data: pd.DataFrame) -> pd.DataFrame:
        return data.dropna(axis = 1, how = 'all')
    
    def dropAllZeroVal(self, data: pd.DataFrame) -> pd.DataFrame:
        return data.loc[:, (data != 0).any(axis=0)]
    
    def dropDiffVal(self, data: pd.DataFrame, attList: List) -> pd.DataFrame:
        idCol = data['ride_id']
        if('year' in data.columns):
            data.drop(['year'], axis = 1, inplace = True)
        if('month' in data.columns):
            data.drop(['month'], axis = 1, inplace = True)
        if('day' in data.columns):
            data.drop(['day'], axis = 1, inplace = True)
        if('hour' in data.columns):
            data.drop(['hour'], axis = 1, inplace = True)
        data.drop(['label', 'ride_id', 'laenge'], axis = 1, inplace = True)
        official_feature = ["avg_speed_kmh", "occurrences", "duration", "population"]
        data.drop(official_feature, axis = 1, inplace = True)
        if(not attList):
            return data
        return data.drop(attList, axis = 1), idCol
    
    def updateLabelEmpty(self, data: pd.DataFrame) -> pd.DataFrame:
        data['label_reg'] = data['label_reg'].fillna(0)
        return data
    
class ModelTrainWorker():
    def __init__(self) -> None:
        pass

    def split(self, data, idCol) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        data['ride_id'] = idCol
        data_orig = data[data['ride_id'] < 1000000]
        data_alt = data[data['ride_id'] >= 1000000]
        # print(data_alt.head())
        data_X = data_orig.loc[:, data_orig.columns != 'label_reg']
        data_y = data_orig.loc[:, data_orig.columns == 'label_reg']
        groupList = list()
        for item in data_X['ride_id']:
            if(item > 1000000):
                groupList.append(str(item - 1000000))
                # print(item, item - 1000000)
            else:
                groupList.append(str(item))
                # print(item, item)
        # print(data_X[data_X['ride_id'] > 1000000].iloc[:10])
        # print(groupList[:10])
        # sgkf = GroupKFold(n_splits = 5)
        # for i, (train_idx, test_idx) in enumerate(sgkf.split(data_X, data_y, groups = groupList)):
        #     break
        # X_train = data_X[data_X.index.isin(train_idx)]
        # y_train = data_y[data_y.index.isin(train_idx)]
        # X_test = data_X[data_X.index.isin(test_idx)]
        # y_test = data_y[data_y.index.isin(test_idx)]
        # X_train = data_X.loc[train_idx]
        # y_train = data_y.loc[train_idx]
        # X_test = data_X.loc[test_idx]
        # y_test = data_y.loc[test_idx]

        X_train, X_test, y_train, y_test = train_test_split(data_X, data_y, test_size = 0.2)
        y_train = y_train['label_reg'].tolist()
        y_test = y_test['label_reg'].tolist()
        i = 0
        # print(y_train)
        for item in X_train['ride_id']:
            # print(data_alt[data_alt['ride_id'] == (int(item) + 1000000)]['label'].values)
            # i += 1
            # if(not (i % 2)):
            #     break
            X_train = X_train.append(data_alt[data_alt['ride_id'] == (int(item) + 1000000)].loc[:, [x for x in data_alt.columns if x != 'label_reg']], ignore_index = True)
            if(not data_alt[data_alt['ride_id'] == (int(item) + 1000000)].loc[:, [x for x in data_alt.columns if x != 'label_reg']].dropna().empty):
                y_train.append(data_alt[data_alt['ride_id'] == (int(item) + 1000000)]['label_reg'].values[0])
            else:
                y_train.append(0)
        # print(y_train)
        # print(np.unique(y_train))
        for item in X_test['ride_id']:
            # if((item + 1000000) in data_alt['ride_id']):
            X_test = X_test.append(data_alt[data_alt['ride_id'] == (int(item) + 1000000)].loc[:, [x for x in data_alt.columns if x != 'label_reg']], ignore_index = True)
            # y_test = y_test.append(pd.DataFrame(data_alt[data_alt['ride_id'] == (int(item) + 1000000)]['label'].values, columns = 'label'), ignore_index = True)
            if(not data_alt[data_alt['ride_id'] == (int(item) + 1000000)].loc[:, [x for x in data_alt.columns if x != 'label_reg']].dropna().empty):
                y_test.append(data_alt[data_alt['ride_id'] == (int(item) + 1000000)]['label_reg'].values[0])
            else:
                y_test.append(0)
        # print(np.unique(y_test))
        y_train = pd.DataFrame(y_train, columns = ['label_reg'])
        y_test = pd.DataFrame(y_test, columns = ['label_reg'])
        data_train = X_train
        data_train.loc[:, 'label_reg'] = y_train
        data_test = X_test
        data_test.loc[:, 'label_reg'] = y_test
        id_train = data_train['ride_id']
        id_test = data_test['ride_id']
        data_train.drop(['ride_id'], axis = 1, inplace = True)
        data_test.drop(['ride_id'], axis = 1, inplace = True)
        # self.data_train = data_train
        # self.data_test = data_test
        return data_train, data_test, id_train, id_test

    def train(self, train_data: pd.DataFrame, label = 'label_reg') -> TabularPredictor:
        predictor = TabularPredictor(label = label, eval_metric = 'root_mean_squared_error', problem_type = 'regression').fit(train_data, verbosity = __VERBOSE__)
        return predictor
    
    def train_rf(self, train_data: pd.DataFrame, label = 'label_reg') -> TabularPredictor:
        print(np.unique(train_data.loc[:,'label_reg']))
        predictor = RandomForestClassifier()
        predictor.fit(train_data.loc[:, [x for x in train_data.columns if x != 'label_reg']], train_data.loc[:,'label_reg'])
        return predictor
    
    def predict(self, predictor: TabularPredictor, test_data: pd.DataFrame, label = 'label_reg') -> None:
        y_pred = predictor.predict(test_data)
        predictor.evaluate(test_data)
        return y_pred
    
    def predict_rf(self, predictor: TabularPredictor, test_data: pd.DataFrame, label = 'label_reg') -> None:
        y_pred = [predictor.predict(test_data.loc[:, [x for x in test_data.columns if x != 'label_reg']])]
        return y_pred

    def analyse_fimportance(self, predictor: TabularPredictor, train_data: Union[pd.DataFrame, TabularDataset]) -> pd.DataFrame:
        return predictor.feature_importance(train_data)

class ModelEvalAnalyser():
    def __init__(self, DBconn = None) -> None:
        if(not DBconn):
            self.__dbconn = dbconn.connect()
            self.__cur = self.__dbconn.cursor()
        else:
            self.__dbconn = DBconn
            self.__cur = self.__dbconn.cursor()

    def getAllIncidentByRideID_batch(self, rideid_list: list):
        _sql = """
               SELECT ride_id, incident FROM berlin_simra_incidents WHERE ride_id IN {}
               """
        
        if(len(rideid_list) == 0):
            return None
        elif(len(rideid_list) == 1):
            formatstr = "(" + str(rideid_list[0]) + ")"
        else:
            formatstr = str(tuple(rideid_list))

        _statement = _sql.format(formatstr)
        self.__cur.execute(_statement)
        resList = list()
        for item in self.__cur.fetchall():
            resList.append(item)

        return resList
    
    def getAllIncidentByRideIDToOSMID_batch(self, rideid_list: list):
        _sql = """
               SELECT DISTINCT osm_id FROM berlin_simra_rides_4k WHERE ride_id IN {}
               """
        if(len(rideid_list) == 0):
            return None
        elif(len(rideid_list) == 1):
            formatstr = "(" + str(rideid_list[0]) + ")"
        else:
            formatstr = str(tuple(rideid_list))
        _statement = _sql.format(formatstr)
        self.__cur.execute(_statement)
        osmidlist = list()
        for item in self.__cur.fetchall():
            osmidlist.append(item[0])

        _sql = """
               SELECT ride_id, incident FROM berlin_simra_incidents WHERE osm_id IN {}
               """
        if(len(osmidlist) == 0):
            return None
        elif(len(osmidlist) == 1):
            formatstr = "(" + str(osmidlist[0]) + ")"
        else:
            formatstr = str(tuple(osmidlist))

        _statement = _sql.format(formatstr)
        self.__cur.execute(_statement)
        resList = list()
        for item in self.__cur.fetchall():
            resList.append(item)

        return resList
    
    def getAvgIncidentByRideID_batch(self, ride_id_Dict: dict, incidentList: list) -> dict:
        incidentDict_true = dict()
        incidentDict_false = dict()
        for incident in incidentList:
            if(incident[0] in ride_id_Dict.keys()):
                if(ride_id_Dict[incident[0]]):
                    incidentDict = incidentDict_true
                else:
                    incidentDict = incidentDict_false
            else:
                continue
            incidentlevel = int(incident[1]) if incident[1] and int(incident[1]) > 0 else 0
            if(incident[0] not in incidentDict.keys()):
                incidentDict[incident[0]] = {"min": 999, "max": -1, "sum": incidentlevel, "count": 1, "avg": incidentlevel}
            else:
                if(incidentlevel > incidentDict[incident[0]]["max"]):
                    incidentDict[incident[0]]["max"] = incidentlevel
                if(incidentlevel < incidentDict[incident[0]]["min"]):
                    if(incidentlevel > 0):
                        incidentDict[incident[0]]["min"] = 0
                    else:
                        incidentDict[incident[0]]["min"] = incidentlevel
                if(incidentlevel > 0):
                    incidentDict[incident[0]]["sum"] += incidentlevel
                incidentDict[incident[0]]["count"] += 1
                incidentDict[incident[0]]["avg"] = incidentDict[incident[0]]["sum"] / incidentDict[incident[0]]["count"]

        return incidentDict_true, incidentDict_false
    
    def calculate_maxProbDiff(self, data):
        maxDict = dict()
        for item in data[['ride_id', 'label_reg']].values:
            if(item[0] < 1000000):
                corRoute = data[data['ride_id'] == item[0] + 1000000]
                if(item[1]):
                    prob = item[1]
                else:
                    prob = 0
                try:
                    probcor = float(corRoute['label_reg'].values[0])
                except:
                    probcor = 0
                if(probcor):
                    if(probcor - prob < 1): 
                        maxDict[item[0]] = abs(probcor - prob)
                else:
                    if(prob < 1):
                        maxDict[item[0]] = abs(prob)

            maxDict = {k: v for k, v in sorted(maxDict.items(), key=lambda item: item[1], reverse = True)}
            if(len(maxDict.keys()) > 5):
                maxDict = dict(islice(maxDict.items(), 5))

        return maxDict



class ModelTrainer():
    def __init__(self) -> None:
        self.preprocess = ModelTrainPreprocessor()
        self.worker = ModelTrainWorker()
        self.analyser = ModelEvalAnalyser()

    def run(self) -> None:
        diff_list = ["x", "y", "z", "acc", "a", "b", "c", "xl", "yl", "zl", "rx", "ry", "rz", "rc"]
        data = self.preprocess.getAllData()
        data = self.preprocess.dropEmptyVal(data)
        data = self.preprocess.dropAllZeroVal(data)
        data, idCol = self.preprocess.dropDiffVal(data, diff_list)
        data = self.preprocess.updateLabelEmpty(data)

        data_train, data_test, id_train, id_test = self.worker.split(data, idCol)
        print(data_train)
        print(data_test)

        # print(data_train.iloc[:, :10])

        # for item in id_test:
        #     if((item - 1000000) in id_train):
        #         print('Leak detected')
        #         print(str(item) + ' in test set')
        #         print(str(item - 1000000) + ' in training set')

        # print(data_train.columns)
        # print(data_test.columns)

        predictor = self.worker.train(data_train)
        # print(predictor)
        y_pred = self.worker.predict(predictor, data_test)
        # print(y_pred)
        feature_importance = self.worker.analyse_fimportance(predictor, data_train)
        feature_importance.to_csv('feature_importance.csv', index = True)
        print(feature_importance)

        ride_id_dict = dict()
        # print(id_test)
        # print(y_pred)
        for rideid, ypred in zip(id_test, y_pred):
            ride_id_dict[rideid] = ypred

        incidentList = self.analyser.getAllIncidentByRideIDToOSMID_batch(id_test)
        incidentDict_true, incidentDict_false = self.analyser.getAvgIncidentByRideID_batch(ride_id_dict, incidentList)
        maxDict = self.analyser.calculate_maxProbDiff(data)
        print(maxDict)
        # print(incidentDict_true)
        # print(incidentDict_false)



if __name__ == "__main__":
    worker = ModelTrainer()
    worker.run()