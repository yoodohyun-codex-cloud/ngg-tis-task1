"""Explicit finite-precision inverse-volume-ECDF definitions; inert import."""
import bisect,math
CANONICAL='full_stable_sorted_cumulative_total_v1'
POSITIVE_SUM='positive_weight_unsorted_sum_v1'
def require(ok,message):
 if not ok:raise ValueError(message)
def inverse_ecdf_index(cumulative,denominator,fraction):
 """Exact side=left finite ordered inverse; no epsilon or denominator repair."""
 require(len(cumulative)>0 and math.isfinite(denominator)and denominator>0 and 0<fraction<1,'Positive finite ECDF normalization')
 return min(bisect.bisect_left(cumulative,fraction*denominator),len(cumulative)-1)
def quantile(np,values,weights,fraction,definition):
 values=np.asarray(values,float);weights=np.asarray(weights,float);require(values.shape==weights.shape and values.ndim==1 and np.isfinite(values).all()and np.isfinite(weights).all()and np.all(weights>=0),'Finite one-dimensional scalar and nonnegative volume/area weights')
 positive=np.flatnonzero(weights>0);require(len(positive)>0,'Positive ECDF mass')
 if definition==CANONICAL:
  native=np.arange(len(values));v=values;w=weights
 elif definition==POSITIVE_SUM:native=positive;v=values[positive];w=weights[positive]
 else:raise ValueError('Unregistered producer ECDF definition')
 order=np.argsort(v,kind='stable');cumulative=np.cumsum(w[order]);unsorted_total=float(np.sum(w));sorted_total=float(cumulative[-1]);denominator=sorted_total if definition==CANONICAL else unsorted_total;threshold=float(fraction*denominator);index=inverse_ecdf_index(cumulative,denominator,fraction)
 require(index==min(int(np.searchsorted(cumulative,threshold,side='left')),len(order)-1),'Standard exact inverse must reproduce producer searchsorted(side=left)')
 previous=index-1;following=min(index+1,len(order)-1);selected=int(native[order[index]]);before=float(cumulative[previous])if index else 0.;at=float(cumulative[index]);nxt=float(cumulative[following]);value=float(v[order[index]])
 return dict(definition=definition,value=value,fraction=float(fraction),normalization_denominator=denominator,unsorted_weight_sum=unsorted_total,sorted_cumulative_total=sorted_total,threshold=threshold,selected_sorted_index=index,selected_native_index=selected,selected_weight=float(w[order[index]]),cumulative_before=before,cumulative_at=at,cumulative_next=nxt,threshold_minus_previous=threshold-before,selected_CDF_minus_threshold=at-threshold,previous_value=float(v[order[previous]])if index else None,next_value=float(v[order[following]]),next_value_gap=float(v[order[following]])-value,previous_value_gap=value-float(v[order[previous]])if index else None,zero_weight_rows_in_sort=int(np.count_nonzero(w==0)),total_rows_in_sort=len(v),side='left',stable_sort=True,values_or_weights_changed=False)
def comparison(np,values,weights,fraction,producer_definition,saved):
 producer=quantile(np,values,weights,fraction,producer_definition);canonical=quantile(np,values,weights,fraction,CANONICAL);legacy=quantile(np,values,weights,fraction,POSITIVE_SUM);limit=1e-10+2e-7*abs(float(saved))
 return dict(saved_original_value=float(saved),producer=producer,common_canonical=canonical,failed_GUI_v1_definition=legacy,absolute_error_producer_to_saved=abs(producer['value']-saved),absolute_error_canonical_to_saved=abs(canonical['value']-saved),absolute_error_legacy_GUI_to_saved=abs(legacy['value']-saved),canonical_minus_original_producer=canonical['value']-producer['value'],regression_absolute_limit=limit,producer_matches_saved_with_unchanged_limit=abs(producer['value']-saved)<=limit,canonical_differs_from_producer=canonical['value']!=producer['value'],legacy_GUI_matches_saved_with_unchanged_limit=abs(legacy['value']-saved)<=limit,diagnosis='Actual values/CDF thresholds preserved; source-definition mismatch is a hypothesis until these measured comparisons are reviewed')
