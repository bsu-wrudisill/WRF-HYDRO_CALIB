module test
contains

! ----- Subroutines -----
subroutine readnc(input_file_name, x, xlen, output_file_name)
  use netcdf
  implicit none 
  character (len = *) :: input_file_name
  character (len = *) :: output_file_name
  !character (len = *), parameter :: varname = "streamflow"
  integer :: x, xlen, ncid, qvarid, status
  integer :: data(xlen) 
  real :: scalefac(1), output(1)
  !f2py intent(out) output
  
  ! open the file 
  status = nf90_open(input_file_name, NF90_NOWRITE, ncid)
  call check(status)  
 
  !! get the variable 
  status = nf90_inq_varid(ncid, "streamflow", qvarid)
  call check(status)  
  
  !! get the 'scale factor'. streamflow is stored as an integer
  !! we must multiply the int by the scale fac to get the correct number 
  status = nf90_get_att(ncid, qvarid, "scale_factor", scalefac)
  call check(status)  
  
  !! get the streamflow data from the file 
  status = nf90_get_var(ncid, qvarid, data)
  call check(status)  
    
  !! multiply the data by the scale factor  
  output = real(data(x))*scalefac

  ! write the data to a text file 
  open (10, file=output_file_name, status='unknown', position='append')
  write(10, *) trim(input_file_name), ',', output
  close(10)
  
  ! close the netcdf file  
  status = nf90_close(ncid)
  
end subroutine readnc
!
!
subroutine check(status)
  use netcdf
  implicit none
  integer, intent ( in) :: status
  
  if(status /= nf90_noerr) then 
  print *, trim(nf90_strerror(status))
  stop "Stopped"
  end if
end subroutine check  
!
!--- End Subroutines 
end module test 
