
import React,{useEffect,useState} from 'react'
import {View,Text,FlatList,StyleSheet} from 'react-native'
type Mission = { id: string; title: string }
export default function Missions(){
 const [m,setM]=useState<Mission[]>([])
 useEffect(()=>{fetch('/v1/world/missions').then(r=>r.json()).then(d=>setM(d.missions||[]))},[])
 return(
  <View style={s.c}>
   <Text style={s.t}>Scan Missions</Text>
   <FlatList data={m} keyExtractor={i=>i.id} renderItem={({item})=>(<Text style={s.r}>{item.title}</Text>)}/>
  </View>
 )
}
const s=StyleSheet.create({c:{flex:1,backgroundColor:"#000",padding:20},t:{color:"#fff",fontSize:22},r:{color:"#ccc"}})
