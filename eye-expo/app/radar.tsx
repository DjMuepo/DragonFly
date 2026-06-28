import * as React from 'react';
import { View, Text, StyleSheet, Pressable, ScrollView } from 'react-native';
import { getDiscoveryRadar } from '../src/lib/api';

export default function RadarScreen() {
  const [data, setData] = React.useState<any>(null);

  const load = async () => {
    try {
      const res = await getDiscoveryRadar({lat:34.0, lon:-118.2});
      setData(res);
    } catch (e) {
      console.warn(e);
    }
  };

  React.useEffect(() => { load(); }, []);

  return (
    <ScrollView style={styles.container} contentContainerStyle={{padding:16,gap:12}}>
      <Text style={styles.title}>Discovery Radar</Text>
      <Text style={styles.subtitle}>Nearby objects, missions, printers, and repair opportunities.</Text>

      {data?.items?.map((item:any, idx:number)=>{
        return (
          <View key={idx} style={styles.card}>
            <Text style={styles.type}>{item.type.toUpperCase()}</Text>
            <Text style={styles.label}>{item.label || item.name}</Text>
            {item.distance_km ? (
              <Text style={styles.meta}>{item.distance_km} km away</Text>
            ) : null}
          </View>
        )
      })}

      <Pressable style={styles.reload} onPress={load}>
        <Text style={styles.reloadText}>Refresh Radar</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container:{flex:1, backgroundColor:'#000'},
  title:{color:'#fff',fontSize:24,fontWeight:'800'},
  subtitle:{color:'#aaa',fontSize:13},
  card:{backgroundColor:'#0b0b0b',borderWidth:1,borderColor:'#1f1f1f',borderRadius:16,padding:14},
  type:{color:'#777',fontSize:11},
  label:{color:'#fff',fontSize:16,fontWeight:'700'},
  meta:{color:'#aaa',fontSize:12},
  reload:{borderWidth:1,borderColor:'#333',padding:14,borderRadius:14,alignItems:'center'},
  reloadText:{color:'#fff',fontWeight:'700'}
});
