
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { useRouter } from 'expo-router';
import { useSnapStore } from '../../src/lib/useSnapStore';

const QUICK_ACTIONS = [
  { label: "Make stronger", apply: (p:any)=>({...p, thickness:(p?.thickness??1)*1.15})},
  { label: "Make lighter", apply: (p:any)=>({...p, thickness:(p?.thickness??1)*0.9})},
  { label: "Make bigger", apply: (p:any)=>({...p, aspect_ratio:(p?.aspect_ratio??1)*1.1})},
  { label: "Make smaller", apply: (p:any)=>({...p, aspect_ratio:(p?.aspect_ratio??1)*0.92})},
  { label: "Smooth edges", apply: (p:any)=>({...p, has_fillet:true})},
];

export default function EditScreen(){
  const router = useRouter();
  const params = useSnapStore((s:any)=>s.structuralParams);
  const setParams = useSnapStore((s:any)=>s.setStructuralParams);

  const apply = (fn:any)=>{
    const next = fn(params||{});
    setParams(next);
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Edit your design</Text>
      <Text style={styles.subtitle}>Tap simple actions to refine your object.</Text>

      <View style={styles.panel}>
        {QUICK_ACTIONS.map((a)=>(
          <Pressable key={a.label} style={styles.card} onPress={()=>apply(a.apply)}>
            <Text style={styles.cardText}>{a.label}</Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.actions}>
        <Pressable style={styles.primary} onPress={()=>router.push('/snap/rotatable')}>
          <Text style={styles.primaryText}>Preview</Text>
        </Pressable>

        <Pressable style={styles.secondary} onPress={()=>router.back()}>
          <Text style={styles.secondaryText}>Back</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
 container:{flex:1,backgroundColor:'#000',padding:16,gap:12},
 title:{color:'#fff',fontSize:24,fontWeight:'800'},
 subtitle:{color:'#bdbdbd',fontSize:13},
 panel:{
   borderWidth:1,
   borderColor:'#1f1f1f',
   backgroundColor:'#0b0b0b',
   borderRadius:18,
   padding:14,
   gap:10
 },
 card:{
   borderWidth:1,
   borderColor:'#1f1f1f',
   backgroundColor:'#060606',
   borderRadius:14,
   padding:14,
   alignItems:'center'
 },
 cardText:{color:'#fff',fontWeight:'700'},
 actions:{marginTop:'auto',gap:10},
 primary:{backgroundColor:'#fff',borderRadius:14,paddingVertical:14,alignItems:'center'},
 primaryText:{color:'#000',fontWeight:'800'},
 secondary:{borderRadius:14,paddingVertical:14,alignItems:'center',borderWidth:1,borderColor:'#2a2a2a'},
 secondaryText:{color:'#fff',fontWeight:'800'}
});
